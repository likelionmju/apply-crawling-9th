Likelion Apply Crawler Project
===

## 요약

[멋쟁이 사자처럼 9기 지원페이지](https://apply.likelion.org)에 지원한 지원자의 정보를 크롤링하여 정리

## 데모

### 성공

![성공](success_demo.gif)

### 실패

![실패](fail_demo.gif)

## 실행 전

1. Chrome 버전에 맞는 [ChromeDriver](https://chromedriver.chromium.org/downloads) 를 `./`에 다운
1. `secrets.json`에 다음 정보를 작성한다.
    + `ADMIN_ID`: 관리자 아이디
    + `ADMIN_PASSWORD`: 관리자 비밀번호
    + `EXCLUDES`: 제외할 사람들 이름 _(없다면 빈 리스트)_
    + `ADMIN_ID`: 질문 목록 _(질문 번호는 제외)_

### `secrets.json` 작성 예시

```json
{
  "ADMIN_ID": "00@likelion.org",
  "ADMIN_PASSWORD": "xxxxxxxx",
  "EXCLUDES": [
    "김길동",
    "박길동"
  ],
  "QUESTIONS": [
    "질문",
    "질문",
    "질문",
    "질문",
    "질문"
  ]
}
```

## 실행 방법

1. `git clone https://github.com/likelionmju/apply_crawling.git`
1. `python3 -m venv venv`
1. mac OS: `source venv/bin/activate`  
   Windows: `venv/Scripts/activate`
1. `pip install -r requirements.txt`
1. `python src/main.py`

## 작동 순서

1. [멋쟁이 사자처럼 9기 지원페이지](https://apply.likelion.org)에 로그인
   ```python
   def login(admin_id: str, admin_password: str, with_headless: bool = True) -> dict:
      ...
   ```
1. 일부 제외할 사람 외에 모든 지원자 정보 취합
   ```python
   def request_univ_page_source(univ_code: str, login_info: dict) -> str:
        ...
   
   def extract_all_applicant_pks(univ_page_source: str) -> list:
        ...
   
   def request_applicant_source(applicant_pk: str, login_info: dict) -> str:
        ...
   
   def parse_applicant_page(page: str, q_count: int) -> Applicant:
        ...
   ```
1. 지원자가 제출한 휴대폰 번호가 `000-0000-0000`의 형식을 따르지 않는 경우,  
   변경
   ```python
   applicant.format_phone_num()
   ```
1. `../지원자 서류/`내에 지원자 별로 `학과_학번_이름`폴더 생성
   ```python
   if not applicant.root_dir.exists():
        applicant.root_dir.mkdir()
   ```
1. 지원자가 별도의 파일을 제출했다면, 파일을 다운로드
   ```python
   def download_applicant_file(applicant: Applicant) -> None:
        ...
   ```
1. 파일의 확장자가 `.zip` 이면,  
   `../지원자 서류/학과_학번_이름/시간표 및 포트폴리오`에 압축해제
   ```python
   def unzip(target: Path, to) -> None:
        ...
   ```
1. 다운로드한 파일의 확장자가 `.png`, `.jpg`, `.jpeg`인 경우,  
   파일명을 시간표로 변경
1. 다운로드한 파일의 확장자가 `.pdf`, `.docx`, `.hwp`인 경우,  
   파일명을 포트폴리오로 변경
   ```python
   def reformat_file(file: Path) -> None:
        ...
   ```
1. 지원자의 정보를 `.docx`로 정리
   ```python
   def export_docx(applicant: Applicant) -> None:
        ...
   ```

### `.docx` 출력 예시

```text
이름: 홍길동
입학 년도: 2018년
전공: 국어국문학과
전화번호: 010-0000-0000
이메일: gildong@gildong.com
GitHub: X
SNS: X

1. 질문
답변

2. 질문
답변

3. 질문
답변

4. 질문
답변

5. 질문
답변
```

## 사용 라이브러리

- `beautifulsoup4 v4.9.3`
- `pathos v0.2.7`
- `python-docx v0.8.10`
- `requests v2.25.1`
- `selenium v3.141.0`
- `yaspin v1.4.1`

## 개발 환경

- `IntelliJ IDEA 2020.3.2 (Ultimate Edition)`
- `macOS Big Sur v11.2.2`
- `python 3.8.5`

## 기타

- `Pipe-and-Filter` 사용
- `pathos.multiprocessing`으로 Multiprocessing 구현
- 압축된 파일에 한글이 포함되어 있는 경우, 파일 명이 깨지는 것을 방지

## 만든 사람

- [AiRini](https://github.com/ygnaiih1680) 명지대학교 융합소프트웨어학부 응용소프트웨어전공 18학번 

