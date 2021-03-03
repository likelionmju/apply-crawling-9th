from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from pathlib import Path
from multiprocessing import Pool
import bs4 as bs
import csv
import platform
import os
import requests
import zipfile
# import time


def unzip(target, to):
    print(to)
    with zipfile.ZipFile(target) as zip_file:
        zip_file.extractall(f"{to}")


def download_url(url, save_path, chunk_size=128):
    # source: https://stackoverflow.com/a/9419208
    r = requests.get(url, stream=True)
    with open(save_path, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)


def is_sns(link):
    for t in sns_list:
        if t in link:
            return True
    return False


def is_img(img):
    return Path(img).suffix in img_extensions


def download_applicant_file(applicant):
    if applicant["file"] == "X":
        return
    path = f"./지원자서류/{applicant['major']} {applicant['entrance_year']} {applicant['name']}"
    if not os.path.exists(path):
        os.mkdir(path)
    file_name = f"{path}/{applicant['file'].split('/')[-1]}"
    if is_img(file_name):
        file_name = f"{path}/시간표.{Path(file_name).suffix}"
    download_url(applicant["file"], file_name)
    if Path(file_name).suffix == "zip":
        unzip(file_name, f"{path}/시간표 및 포트폴리오")
        os.remove(file_name)


newTab = f"{Keys.COMMAND if platform.system() == 'Darwin' else Keys.CONTROL}t"
sns_list = ("facebook", "instagram", "twitter")
img_extensions = ("png", "jpg", "jpeg", "PNG", "JPG", "JPEG")


class Crawler:
    def __init__(self, exclude_applicants):
        options = webdriver.ChromeOptions()
        options.headless = True
        self.__driver = webdriver.Chrome(executable_path="./chromedriver", options=options)

        self.__univ_code = ""
        self.__exclude_applicants = exclude_applicants
        self.__applicant_urls = 0
        self.__applicants = dict()
        self.__domain = "https://apply.likelion.org"
        self.__applicant_sources = list()

    def __enter__(self):
        os.mkdir("./지원자서류")
        self.__get_applicant_links()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__driver.close()

    def __str__(self):
        return "\r\n".join([f"{ap['major']} {ap['entrance_year']} {ap['name']}" for ap in self.__applicants.values()])

    def __get_page_source_by_a_tag(self, a):
        self.__driver.get(a.get_attribute("href"))
        return self.__driver.page_source

    def __get_applicant_links(self):
        self.__driver.get(f"{self.__domain}/apply/")
        admin_id = input("관리자 아이디: ")
        admin_pass = input("관리자 비밀번호: ")
        self.__driver.find_element_by_id("id_username").send_keys(admin_id)
        self.__driver.find_element_by_id("id_password").send_keys(admin_pass)

        self.__driver.find_element_by_xpath("//button[@type='submit']").submit()
        self.__univ_code = admin_id.split('@')[0]
        applicant_page = f"{self.__domain}/apply/univ/{self.__univ_code}"
        self.__driver.get(applicant_page)

        total = len(self.__driver.find_elements_by_css_selector(".applicant_page > a"))
        for i in range(1, total + 1):
            self.__driver.get(applicant_page)
            a = self.__driver.find_element_by_xpath(f"//*[@id='likelion_num']/div[3]/a[{i}]")
            self.__applicant_sources.append(self.__get_page_source_by_a_tag(a))

    def __crawl_applicant(self, source):
        soup = bs.BeautifulSoup(source, features="html.parser")
        user_info_container = soup.select_one("#likelion_num")
        user_answer_container = soup.select_one(".answer_view > .applicant_detail_page")

        user_name = user_info_container.find("h3").string
        if user_name in self.__exclude_applicants:
            return
        user_info_list = user_info_container.find_all("div", {"class": "row"})
        user_answer_list = user_answer_container.find_all("div", {"class": "m_mt"})
        additional = [user_info.contents[1].get("href") for user_info in user_info_list[2:]]
        git = sns = applicant_file = None

        for item in additional:
            if item is None:
                continue
            if "git" in item:
                git = item
            elif is_sns(item):
                sns = item
            elif "cdn" in item:
                applicant_file = item

        self.__applicants[user_name] = {
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

        phone_num = self.__applicants[user_name]["phone_num"]
        if len(phone_num) == 11:
            formatting_phone_num = [phone_num[:3], phone_num[3:7], phone_num[7:]]
            self.__applicants[user_name]["phone_num"] = "-".join(formatting_phone_num)

        download_applicant_file(self.__applicants[user_name])

    def start_crawling_non_parallel(self):
        for s in self.__applicant_sources:
            self.__crawl_applicant(s)

    def start_crawling_parallel(self, processes=4):
        pool = Pool(processes)
        pool.map(self.__crawl_applicant, self.__applicant_sources)
        pool.close()

    def export_csv(self):
        with open("지원자목록.csv", "w", newline="", encoding="utf-8") as file:
            keys_to_header = {
                "name": "이름",
                "entrance_year": "입학 년도",
                "major": "전공",
                "phone_num": "전화번호",
                "email": "이메일",
                "git": "github",
                "sns": "SNS",
                "file": "file",
                "q1": "지원 동기",
                "q2": "만들고 싶은 서비스",
                "q3": "가장 기억에 남는 활동과 느낀 점",
                "q4": "기억에 남는 프로그래밍 경험과 느낀 점 또는 배우고 싶은 것",
                "q5": "1학기 시간표와 opt(포트폴리오)"
            }
            writer = csv.DictWriter(file, fieldnames=keys_to_header.keys())
            writer.writerow(keys_to_header)
            for applicant in self.__applicants.values():
                writer.writerow(applicant)


if __name__ == "__main__":
    with Crawler(exclude_applicants=["한준혁", "김예빈", "박성제"]) as crawler:
        crawler.start_crawling_non_parallel()
        crawler.export_csv()
        print(crawler)
    # for i in range(4, 65, 4):
    #     with Crawler(exclude_applicants=["한준혁", "김예빈", "박성제"]) as crawler:
    #         start = time.time()
    #         crawler.start_crawling_non_parallel()
    #         # crawler.export_csv()
    #         # print(crawler)
    #     print(f"process 갯수: {i} 소요시간: {time.time() - start}")
