import re
from pathlib import Path


class Applicant:
    __phone_num_pattern = re.compile("[0-9]{3}-[0-9]{4}-[0-9]{4}")
    __idx = 0

    def __init__(self,
                 name: str,
                 entrance_year: str,
                 major: str,
                 phone_num: str,
                 email: str,
                 answers: list,
                 git: str,
                 sns: str,
                 cdn_file: str,
                 is_exclude: bool = False,
                 ) -> None:

        Applicant.__idx += 1
        self.__idx = Applicant.__idx
        self.name: str = name
        self.entrance_year: str = entrance_year
        self.major: str = major
        self.phone_num: str = phone_num
        self.email: str = email
        self.answers: list = answers
        self.is_exclude: bool = is_exclude
        self.git: str = git or "X"
        self.sns: str = sns or "X"
        self.cdn_file: str = cdn_file or "X"
        if not is_exclude:
            self.root_dir: Path = Path(f"../지원자 서류/{self.major}_{self.entrance_year[2:]}_{self.name}")

    def __str__(self) -> str:
        return \
            f"""이름: {self.name}
입학 년도: {self.entrance_year}
전공: {self.major}
전화번호: {self.phone_num}
이메일: {self.email}"""

    @staticmethod
    def get_exclude_applicant():
        return Applicant("", "", "", "", "", [], "", "", "", True)

    def __is_phone_num_formatted(self) -> bool:
        return self.__phone_num_pattern.fullmatch(self.phone_num) is not None

    def format_phone_num(self) -> None:
        if not self.__is_phone_num_formatted():
            self.phone_num = "-".join([self.phone_num[:3], self.phone_num[3:7], self.phone_num[7:]])

    def has_file(self):
        return self.cdn_file != "X"

    def information_stringify(self):
        return [
            f"이름: {self.name}",
            f"입학 년도: {self.entrance_year}년",
            f"전공: {self.major}",
            f"전화번호: {self.phone_num}",
            f"이메일: {self.email}",
            f"GitHub: {self.git}",
            f"SNS: {self.sns}",
        ]
