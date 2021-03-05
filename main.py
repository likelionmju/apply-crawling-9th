from selenium.webdriver import Chrome, ChromeOptions
from pathos.multiprocessing import ProcessPool
from pathlib import Path
from multiprocessing import Manager
import bs4 as bs
import csv
import os
import requests
import zipfile
import time
import copy
import re


class LikelionApplyCrawlerSettings:

    def __init__(self) -> None:
        self.driver_options = ChromeOptions()
        self.driver_options.headless = True

        # self.admin_id = input("관리자 아이디: ")
        # self.admin_pass = input("관리자 비밀번호: ")
        # self.univ_code = self.admin_id.split('@')[0]
        # self.
        # self.
        # self.


def is_sns(link) -> bool:
    for lk in sns_list:
        if lk in link:
            return True
    return False


def is_img(img) -> bool:
    return Path(img).suffix in img_extensions


def unzip(target, to) -> None:
    with zipfile.ZipFile(target) as zip_file:
        zip_file.extractall(to)


def get_n_deep_copies(target, n: int) -> list:
    return [copy.deepcopy(target) for _ in range(n)]


def download_file_by_url(u, save_path, chunk_size=128) -> None:
    # source: https://stackoverflow.com/a/9419208
    r = requests.get(u, stream=True)
    with open(save_path, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)


def download_applicant_file(applicant: dict):
    if applicant["name"] in exclude_applicants:
        return
    if applicant["file"] == "X":
        return
    path = f"./지원자 서류/{applicant['major']} {applicant['entrance_year']} {applicant['name']}"
    if not os.path.exists(path):
        os.mkdir(path)
    file_name = f"{path}/{applicant['file'].split('/')[-1]}"
    if is_img(file_name):
        file_name = f"{path}/시간표{Path(file_name).suffix}"
    download_file_by_url(applicant["file"], file_name)
    if Path(file_name).suffix == ".zip":
        unzip(file_name, f"{path}/시간표 및 포트폴리오")
        os.remove(file_name)


class LikelionApplyCrawler:
    domain = "https://apply.likelion.org"
    apply_url = f"{domain}/apply"
    univ_url = f"{apply_url}/univ/"
    applicant_url = f"{apply_url}/applicant"

    __id_path = "id_username"
    __password_path = "id_password"
    __login_path = "//button[@type='submit']"
    __applicant_info_container_path = "#likelion_num"
    __answered_applicant_count_path = f"{__applicant_info_container_path} > div:nth-child(2) > p:nth-child(2)"
    __applicant_answer_container_path = ".answer_view > .applicant_detail_page"
    __applicants_path = f"{__applicant_info_container_path} > div.applicant_page > a"

    __applicant_count_regex = re.compile(" [0-9]+")

    __html_parser = "html.parser"

    def __init__(self, admin_id: str, admin_pass: str, headless: bool = True) -> None:
        self.__admin_id = admin_id
        self.__admin_pass = admin_pass
        self.headless = headless
        self.univ_url += self.__admin_id.split('@')[0]
        self.applicant_pks = None
        print("crawling start...")

    def __enter__(self):
        self.cookies = {ck["name"]: ck["value"] for ck in self.login()}
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"async multi processing time: {time.time() - start_time}s")

    def login(self) -> dict:
        driver_options = ChromeOptions()
        driver_options.headless = self.headless
        with Chrome(executable_path="./chromedriver", options=driver_options) as driver:
            driver.get(self.apply_url)
            driver.find_element_by_id(self.__id_path).send_keys(self.__admin_id)
            driver.find_element_by_id(self.__password_path).send_keys(self.__admin_pass)
            driver.find_element_by_xpath(self.__login_path).submit()
            print(f"finish login time: {time.time() - start_time}s")
            return driver.get_cookies()

    def request_univ_page_source(self) -> str:
        return requests.get(self.univ_url, cookies=self.cookies).text

    #
    # def get_answered_applicant_count(self, univ_page_source: str) -> int:
    #     univ_page = bs.BeautifulSoup(univ_page_source, features=self.__html_parser)
    #     info_text = univ_page.select_one(self.__answered_applicant_count_path).string
    #     find = self.__applicant_count_regex.search(info_text).group()
    #     return int(find)

    def extract_all_applicant_pks(self, univ_page_source: str) -> None:
        univ_page = bs.BeautifulSoup(univ_page_source, features=self.__html_parser)
        self.applicant_pks = [applicant.get("href").split("/")[-1]
                              for applicant in univ_page.select(self.__applicants_path)]

    def request_applicant_source(self, applicant_pk: str) -> str:
        return requests.get(f"{self.applicant_url}/{applicant_pk}", cookies=self.cookies).text

    def parse_applicant_page(self, page) -> dict:
        try:
            soup = bs.BeautifulSoup(page, features="html.parser")
            applicant_info_container = soup.select_one(self.__applicant_info_container_path)
            applicant_answer_container = soup.select_one(self.__applicant_answer_container_path)

            applicant_name = applicant_info_container.find("h3").string
            if applicant_name in exclude_applicants:
                return {"name": applicant_name}
            user_info_list = applicant_info_container.select("div.row")
            user_answer_list = applicant_answer_container.select("div.m_mt")
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

            applicant = {
                "name": applicant_name,
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
            phone_num = applicant["phone_num"]
            if len(phone_num) == 11:
                formatting_phone_num = [phone_num[:3], phone_num[3:7], phone_num[7:]]
                applicant["phone_num"] = "-".join(formatting_phone_num)
            return applicant
        except AttributeError:
            print("error")

    # def export_csv(self) -> None:
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
    import sys
    sys.setrecursionlimit(3000)
    required_dir = Path("./지원자 서류")
    if not required_dir.exists():
        required_dir.mkdir()
    sns_list = ("facebook", "instagram", "twitter")
    img_extensions = (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG")
    a_id = input("관리자 ID: ")
    a_pass = input("관리자 PW: ")
    exclude_applicants = input("제외할 사람: ").split() or ["테스트", "한준혁", "김예빈", "박성제"]

    # manager = Manager()
    # applicants = manager.dict()
    # sources = manager.list()
    # applicant_urls = manager.list()
    # with LikelionApplyCrawler() as c:
    #     start_time = time.time()
    #     c.login()
    #     c.load_univ_page()
    #     for url in c.get_all_applicant_url():
    #         parse_page(url)
    #     c.export_csv()
    # print(f"single processing time: {time.time() - start_time}")
    start_time = time.time()
    with LikelionApplyCrawler(admin_id=a_id, admin_pass=a_pass) as c:
        source = c.request_univ_page_source()
        c.extract_all_applicant_pks(source)
        print(f"finish extract pks time: {time.time() - start_time}s")
        with ProcessPool() as main_pool:
            applicant_sources = main_pool.amap(c.request_applicant_source, c.applicant_pks).get()
            print(f"finish request sources time: {time.time() - start_time}s")
            applicants = main_pool.amap(c.parse_applicant_page, applicant_sources).get()
            print(f"total applicants count: {len(applicants)}")
            main_pool.map(download_applicant_file, applicants)
            print(f"finish download time: {time.time() - start_time}s")

        # with ProcessPool(nodes=4) as main_pool:
        #     c.load_univ_page()
        #     c.extract_all_applicant_url()
        #     main_pool.map(c.add_page_source, applicant_urls)
        # c.export_csv()
        # with ProcessPool(nodes=4) as sub_pool:
        #     sub_pool.map(c.parse_applicant_page, sources)


