from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.remote.webelement import WebElement
from pathlib import Path
from multiprocessing import Manager
from enum import Enum
import bs4 as bs
import csv
import platform
import os
import requests
import zipfile
from pathos.multiprocessing import ProcessPool
import dill


# import time


class ProcessingOption(Enum):
    MULTI_PROCESSING = 0
    SINGLE_PROCESSING = 1


class LikelionApplyCrawlerSettings:

    def __init__(self, processing_option: ProcessingOption = ProcessingOption.MULTI_PROCESSING) -> None:
        self.processing_option = processing_option
        self.driver_options = ChromeOptions()
        self.driver_options.headless = True
        # self.driver_options.add_argument("user-data-dir=./cache")

        self.admin_id = input("관리자 아이디: ")
        self.admin_pass = input("관리자 비밀번호: ")
        self.univ_code = self.admin_id.split('@')[0]

        self.domain = "https://apply.likelion.org"
        self.login_url = f"{self.domain}/apply/"
        self.univ_url = f"{self.domain}/apply/univ/{self.univ_code}"

        self.sns_list = ("facebook", "instagram", "twitter")
        self.img_extensions = (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG")

        self.exclude_applicants = input("제외할 지원자의 이름을 입력해주세요. (여러 명일 경우, 쉼표로 구분합니다.)").split()
        if len(self.exclude_applicants) == 0:
            self.exclude_applicants = ["테스트", "한준혁", "김예빈", "박성제"]


class LikelionApplyCrawler:
    settings = LikelionApplyCrawlerSettings()
    applicants = dict()

    def __init__(self) -> None:
        self.driver = Chrome(executable_path="./chromedriver", options=LikelionApplyCrawler.settings.driver_options)

    def __enter__(self):
        self.driver.get(self.settings.domain)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()

    @staticmethod
    def unzip(target, to) -> None:
        print(to)
        with zipfile.ZipFile(target) as zip_file:
            zip_file.extractall(to)

    @staticmethod
    def download_file_by_url(url, save_path, chunk_size=128) -> None:
        # source: https://stackoverflow.com/a/9419208
        r = requests.get(url, stream=True)
        with open(save_path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)

    @staticmethod
    def get_page_source_by_a_tag(driver: Chrome, a: WebElement) -> str:
        driver.get(a.get_attribute("href"))
        return driver.page_source

    def download_applicant_file(self, applicant):
        if applicant["file"] == "X":
            return
        path = f"./지원자 서류/{applicant['major']} {applicant['entrance_year']} {applicant['name']}"
        if not os.path.exists(path):
            os.mkdir(path)
        file_name = f"{path}/{applicant['file'].split('/')[-1]}"
        print(Path(file_name).suffix)
        if self.is_img(file_name):
            file_name = f"{path}/시간표.{Path(file_name).suffix}"
        self.download_file_by_url(applicant["file"], file_name)
        if Path(file_name).suffix == ".zip":
            self.unzip(file_name, f"{path}/시간표 및 포트폴리오")
            os.remove(file_name)

    def restore_cookies(self):
        with open("cookies.pkl", "rb") as f:
            for cookie in dill.load(f):
                self.driver.add_cookie(cookie)

    def is_sns(self, link) -> bool:
        for t in LikelionApplyCrawler.settings.sns_list:
            if t in link:
                return True
        return False

    def is_img(self, img) -> bool:
        return Path(img).suffix in LikelionApplyCrawler.settings.img_extensions

    def login(self) -> None:
        self.driver.get(LikelionApplyCrawler.settings.login_url)
        # if self.driver.current_url == LikelionApplyCrawler.settings.login_url:
        #     return self.driver
        self.driver.find_element_by_id("id_username").send_keys(LikelionApplyCrawler.settings.admin_id)
        self.driver.find_element_by_id("id_password").send_keys(LikelionApplyCrawler.settings.admin_pass)
        self.driver.find_element_by_xpath("//button[@type='submit']").submit()

        with open("cookies.pkl", "wb") as f:
            dill.dump(self.driver.get_cookies(), f)

    def get_total_applicant_count(self) -> int:
        self.driver.get(LikelionApplyCrawler.settings.univ_url)
        return len(self.driver.find_elements_by_css_selector(".applicant_page > a"))

    def move_to_applicant_page(self, idx):
        self.restore_cookies()
        self.driver.get(LikelionApplyCrawler.settings.univ_url)
        a = self.driver.find_element_by_xpath(f"//*[@id='likelion_num']/div[3]/a[{idx}]")
        self.driver.get(a.get_attribute("href"))

    def parse_applicant_page(self, source) -> str:
        soup = bs.BeautifulSoup(source, features="html.parser")
        user_info_container = soup.select_one("#likelion_num")
        user_answer_container = soup.select_one(".answer_view > .applicant_detail_page")

        user_name = user_info_container.find("h3").string
        if user_name in self.settings.exclude_applicants:
            return ""
        user_info_list = user_info_container.find_all("div", {"class": "row"})
        user_answer_list = user_answer_container.find_all("div", {"class": "m_mt"})
        additional = [user_info.contents[1].get("href") for user_info in user_info_list[2:]]
        git = sns = applicant_file = None

        for item in additional:
            if item is None:
                continue
            if "git" in item:
                git = item
            elif self.is_sns(item):
                sns = item
            elif "cdn" in item:
                applicant_file = item

        LikelionApplyCrawler.applicants[user_name] = {
            "name": user_name,
            "entrance_year": user_info_list[0].contents[1].text,
            "major": user_info_list[0].contents[-2].text,
            "phone_num": user_info_list[1].contents[1].text,
            "email": user_info_list[1].contents[-2].text,
            "git": git if git is not None else "X",
            "sns": sns if sns is not None else "X",
            "file": applicant_file if applicant_file is not None else "X",
            "q1": user_answer_list[0].contents[1].text,
            "q2": user_answer_list[1].contents[1].text,
            "q3": user_answer_list[2].contents[1].text,
            "q4": user_answer_list[3].contents[1].text,
            "q5": user_answer_list[4].contents[1].text,
        }

        phone_num = LikelionApplyCrawler.applicants[user_name]["phone_num"]
        if len(phone_num) == 11:
            formatting_phone_num = [phone_num[:3], phone_num[3:7], phone_num[7:]]
            LikelionApplyCrawler.applicants[user_name]["phone_num"] = "-".join(formatting_phone_num)
        return user_name


def multi_processing_crawl(idx):
    with LikelionApplyCrawler() as crawler:
        crawler.move_to_applicant_page(idx)
        name = crawler.parse_applicant_page(crawler.driver.page_source)
        if name == "":
            return
        crawler.download_applicant_file(LikelionApplyCrawler.applicants[name])


# def __init__(self, exclude_applicants):
#     options = webdriver.ChromeOptions()
#     options.headless = True
#     options.add_argument("user-data-dir=./cache")
#     self.__driver = webdriver.Chrome(executable_path="./chromedriver", options=options)
#
#     self.__univ_code = ""
#     self.exclude_applicants = exclude_applicants
#     self.__applicant_urls = 0
#     self.applicants = dict()
#     self.__domain = "https://apply.likelion.org"
#     self.applicant_sources = list()
#
# def __enter__(self):
#     self.__get_applicant_links()
#     return self
#
# def __exit__(self, exc_type, exc_val, exc_tb):
#     self.__driver.close()
#
# def __str__(self):
#     return "\r\n".join([f"{ap['major']} {ap['entrance_year']} {ap['name']}" for ap in self.applicants.values()])
#
# def __get_page_source_by_a_tag(self, a):
#     self.__driver.get(a.get_attribute("href"))
#     return self.__driver.page_source
#
# @staticmethod
# def download_applicant_file(applicant):
#     if applicant["file"] == "X":
#         return
#     path = f"./지원자 서류/{applicant['major']} {applicant['entrance_year']} {applicant['name']}"
#     if not os.path.exists(path):
#         os.mkdir(path)
#     file_name = f"{path}/{applicant['file'].split('/')[-1]}"
#     if is_img(file_name):
#         file_name = f"{path}/시간표.{Path(file_name).suffix}"
#     download_url(applicant["file"], file_name)
#     if Path(file_name).suffix == "zip":
#         unzip(file_name, f"{path}/시간표 및 포트폴리오")
#         os.remove(file_name)
#
# def __get_applicant_links(self):
#     self.__driver.get(f"{self.__domain}/apply/")
#     admin_id = input("관리자 아이디: ")
#     admin_pass = input("관리자 비밀번호: ")
#     self.__driver.find_element_by_id("id_username").send_keys(admin_id)
#     self.__driver.find_element_by_id("id_password").send_keys(admin_pass)
#
#     self.__driver.find_element_by_xpath("//button[@type='submit']").submit()
#     self.__univ_code = admin_id.split('@')[0]
#     applicant_page = f"{self.__domain}/apply/univ/{self.__univ_code}"
#     self.__driver.get(applicant_page)
#
#     total = len(self.__driver.find_elements_by_css_selector(".applicant_page > a"))
#     for i in range(1, total + 1):
#         self.__driver.get(applicant_page)
#         a = self.__driver.find_element_by_xpath(f"//*[@id='likelion_num']/div[3]/a[{i}]")
#         self.applicant_sources.append(self.__get_page_source_by_a_tag(a))
#
# def crawl_applicant(self, source):
#     soup = bs.BeautifulSoup(source, features="html.parser")
#     user_info_container = soup.select_one("#likelion_num")
#     user_answer_container = soup.select_one(".answer_view > .applicant_detail_page")
#
#     user_name = user_info_container.find("h3").string
#     if user_name in self.exclude_applicants:
#         return
#     user_info_list = user_info_container.find_all("div", {"class": "row"})
#     user_answer_list = user_answer_container.find_all("div", {"class": "m_mt"})
#     additional = [user_info.contents[1].get("href") for user_info in user_info_list[2:]]
#     git = sns = applicant_file = None
#
#     for item in additional:
#         if item is None:
#             continue
#         if "git" in item:
#             git = item
#         elif is_sns(item):
#             sns = item
#         elif "cdn" in item:
#             applicant_file = item
#
#     self.applicants[user_name] = {
#         "name": user_name,
#         "entrance_year": user_info_list[0].contents[1].text,
#         "major": user_info_list[0].contents[-2].text,
#         "phone_num": user_info_list[1].contents[1].text,
#         "email": user_info_list[1].contents[-2].text,
#         "git": git if git is not None else "X",
#         "sns": sns if sns is not None else "X",
#         "file": applicant_file if applicant_file is not None else "X",
#         "q1": user_answer_list[0].contents[1].text,
#         "q2": user_answer_list[1].contents[1].text,
#         "q3": user_answer_list[2].contents[1].text,
#         "q4": user_answer_list[3].contents[1].text,
#         "q5": user_answer_list[4].contents[1].text,
#     }
#
#     phone_num = self.applicants[user_name]["phone_num"]
#     if len(phone_num) == 11:
#         formatting_phone_num = [phone_num[:3], phone_num[3:7], phone_num[7:]]
#         self.applicants[user_name]["phone_num"] = "-".join(formatting_phone_num)
#
#     # self.download_applicant_file(self.applicants[user_name])
#
# def start_crawling_non_parallel(self):
#     for s in self.applicant_sources:
#         self.crawl_applicant(s)
#
# def start_crawling_parallel(self):
#     pool = ParallelPool()
#     pool.map(self.crawl_applicant, self.applicant_sources)
#     pool.close()
#
# def export_csv(self):
#     with open("지원자목록.csv", "w", newline="", encoding="utf-8") as file:
#         keys_to_header = {
#             "name": "이름",
#             "entrance_year": "입학 년도",
#             "major": "전공",
#             "phone_num": "전화번호",
#             "email": "이메일",
#             "git": "github",
#             "sns": "SNS",
#             "file": "file",
#             "q1": "지원 동기",
#             "q2": "만들고 싶은 서비스",
#             "q3": "가장 기억에 남는 활동과 느낀 점",
#             "q4": "기억에 남는 프로그래밍 경험과 느낀 점 또는 배우고 싶은 것",
#             "q5": "1학기 시간표와 opt(포트폴리오)"
#         }
#         writer = csv.DictWriter(file, fieldnames=keys_to_header.keys())
#         writer.writerow(keys_to_header)
#         for applicant in self.applicants.values():
#             writer.writerow(applicant)


if __name__ == "__main__":
    with ProcessPool() as main_pool:
        with LikelionApplyCrawler() as c:
            c.login()
            total = c.get_total_applicant_count()
            main_pool.map(multi_processing_crawl, range(1, total + 1))
    # for i in range(4, 65, 4):
    #     with Crawler(exclude_applicants=["한준혁", "김예빈", "박성제"]) as crawler:
    #         start = time.time()
    #         crawler.start_crawling_non_parallel()
    #         # crawler.export_csv()
    #         # print(crawler)
    #     print(f"process 갯수: {i} 소요시간: {time.time() - start}")
