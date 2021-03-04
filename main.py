from selenium.webdriver import Chrome, ChromeOptions
from multiprocessing import Pool
from pathlib import Path
import bs4 as bs
import csv
import os
import requests
import zipfile

import time


class LikelionApplyCrawlerSettings:

    def __init__(self) -> None:
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

        self.exclude_applicants = input("제외할 지원자의 이름을 입력해주세요. (여러 명일 경우, 공백으로 구분합니다.)").split()
        if len(self.exclude_applicants) == 0:
            self.exclude_applicants = ["테스트", "한준혁", "김예빈", "박성제"]


class LikelionApplyCrawler:

    def __init__(self) -> None:
        self.settings = LikelionApplyCrawlerSettings()
        self.applicants = dict()
        self.cookies = None
        self.univ_page = None
        print("crawling start...")

    def __enter__(self):
        if self.cookies is None:
            self.cookies = {ck["name"]: ck["value"] for ck in self.login()}
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("finished...")

    @staticmethod
    def unzip(target, to) -> None:
        with zipfile.ZipFile(target) as zip_file:
            zip_file.extractall(to)

    @staticmethod
    def download_file_by_url(u, save_path, chunk_size=128) -> None:
        # source: https://stackoverflow.com/a/9419208
        r = requests.get(u, stream=True)
        with open(save_path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)

    def download_applicant_file(self, applicant):
        if applicant["file"] == "X":
            return
        path = f"./지원자 서류/{applicant['major']} {applicant['entrance_year']} {applicant['name']}"
        if not os.path.exists(path):
            os.mkdir(path)
        file_name = f"{path}/{applicant['file'].split('/')[-1]}"
        if self.is_img(file_name):
            file_name = f"{path}/시간표.{Path(file_name).suffix}"
        self.download_file_by_url(applicant["file"], file_name)
        if Path(file_name).suffix == ".zip":
            self.unzip(file_name, f"{path}/시간표 및 포트폴리오")
            os.remove(file_name)

    def is_sns(self, link) -> bool:
        for lk in self.settings.sns_list:
            if lk in link:
                return True
        return False

    def is_img(self, img) -> bool:
        return Path(img).suffix in self.settings.img_extensions

    def login(self):
        with Chrome(executable_path="./chromedriver", options=self.settings.driver_options) as driver:
            driver.get(self.settings.login_url)
            driver.find_element_by_id("id_username").send_keys(self.settings.admin_id)
            driver.find_element_by_id("id_password").send_keys(self.settings.admin_pass)
            driver.find_element_by_xpath("//button[@type='submit']").submit()

            return driver.get_cookies()

    def load_univ_page(self) -> None:
        res = requests.get(self.settings.univ_url, cookies=self.cookies)
        self.univ_page = bs.BeautifulSoup(res.text, features="html.parser")

    def get_all_applicant_url(self) -> list:
        return [f"{self.settings.domain}{a.get('href')}"
                for a in self.univ_page.select("#likelion_num > div.applicant_page > a")]

    def parse_applicant_page(self, page) -> str:
        source = requests.get(page, cookies=self.cookies).text
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

        self.applicants[user_name] = {
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

        phone_num = self.applicants[user_name]["phone_num"]
        if len(phone_num) == 11:
            formatting_phone_num = [phone_num[:3], phone_num[3:7], phone_num[7:]]
            self.applicants[user_name]["phone_num"] = "-".join(formatting_phone_num)
        return user_name

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
            for applicant in self.applicants.values():
                writer.writerow(applicant)


def parse_page(target_url):
    name = c.parse_applicant_page(target_url)
    if name == "":
        return
    c.download_applicant_file(c.applicants[name])


if __name__ == "__main__":
    # with LikelionApplyCrawler() as c:
    #     start_time = time.time()
    #     c.login()
    #     c.load_univ_page()
    #     for url in c.get_all_applicant_url():
    #         parse_page(url)
    #     c.export_csv()
    # print(f"single processing time: {time.time() - start_time}")
    with Pool(processes=4) as main_pool:
        with LikelionApplyCrawler() as c:
            start_time = time.time()
            c.login()
            c.load_univ_page()
            main_pool.imap(parse_page, c.get_all_applicant_url())
            c.export_csv()
    print(f"multi processing time: {time.time() - start_time}")
