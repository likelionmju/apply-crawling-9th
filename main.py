if __name__ == "__main__":
    from selenium import webdriver
    import bs4 as bs
    import csv

    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Chrome(executable_path="./chromedriver", options=options)
    driver.get("https://apply.likelion.org/apply/")
    admin_id = input("관리자 아이디: ")
    admin_pass = input("관리자 비밀번호: ")
    driver.find_element_by_id("id_username").send_keys(admin_id)
    driver.find_element_by_id("id_password").send_keys(admin_pass)

    driver.find_element_by_xpath("//button[@type='submit']").submit()

    univ_code = admin_id.split('@')[0]
    driver.get(f"https://apply.likelion.org/apply/univ/{univ_code}")

    soup = bs.BeautifulSoup(driver.page_source, features="html.parser")

    applicant_list = dict()
    if univ_code == 16:
        exclude_names = ["한준혁", "김예빈", "박성제"]
    else:
        exclude_names = list()

    for applicant in soup.select(".applicant_page > a"):
        applicant_url = applicant["href"]
        driver.get(f"https://apply.likelion.org{applicant_url}")

        soup = bs.BeautifulSoup(driver.page_source, features="html.parser")
        user_info_container = soup.select_one("#likelion_num")
        user_answer_container = soup.select_one(".answer_view > .applicant_detail_page")

        user_name = user_info_container.find("h3").string
        if user_name in exclude_names:
            continue
        print(user_name)
        user_info_list = user_info_container.find_all("div", {"class": "row"})
        user_answer_list = user_answer_container.find_all("div", {"class": "m_mt"})

        additional = [user_info.contents[1].get("href") if user_info.contents[1].get("href") is not None else "제출하지 않음"
                      for user_info in user_info_list[2:]]

        applicant_list[user_name] = {
            "name": user_name,
            "entrance_year": user_info_list[0].contents[1].text,
            "major": user_info_list[0].contents[-2].text,
            "phone_num": user_info_list[1].contents[1].text,
            "email": user_info_list[1].contents[-2].text,
            "additional": ", ".join(additional),
            "q1": user_answer_list[0].contents[1].text,
            "q2": user_answer_list[1].contents[1].text,
            "q3": user_answer_list[2].contents[1].text,
            "q4": user_answer_list[3].contents[1].text,
            "q5": user_answer_list[4].contents[1].text,
        }

        phone_num = applicant_list[user_name]["phone_num"]
        if "-" not in phone_num:
            formatting_phone_num = [phone_num[:3], phone_num[3:7], phone_num[7:]]
            applicant_list[user_name]["phone_num"] = "-".join(formatting_phone_num)

    with open("지원자목록.csv", "w", newline="", encoding="utf-8") as file:
        keys_to_header = {
            "name": "이름",
            "entrance_year": "입학 년도",
            "major": "전공",
            "phone_num": "전화번호",
            "email": "이메일",
            "additional": "추가 제출",
            "q1": "지원 동기",
            "q2": "만들고 싶은 서비스",
            "q3": "가장 기억에 남는 활동과 느낀 점",
            "q4": "기억에 남는 프로그래밍 경험과 느낀 점 또는 배우고 싶은 것",
            "q5": "1학기 시간표와 opt(포트폴리오)"
        }
        writer = csv.DictWriter(file, fieldnames=keys_to_header.keys())
        writer.writerow(keys_to_header)
        for applicant in applicant_list.values():
            writer.writerow(applicant)

    driver.quit()
