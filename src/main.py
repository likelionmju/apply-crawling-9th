from pathlib import Path

from filters import *
from queue import Queue
from pathos.multiprocessing import ProcessPool
from crawler import pickle_applicant,\
    unpickle_applicant,\
    unpickle_all_applicant,\
    send_email_to_applicant,\
    gathering_applicant_data
from json import loads
import markdown2

with open("../secrets.json") as f:
    secrets = loads(f.read())
with open("../data/pass_subject") as p_subject:
    pass_subject = p_subject.read()
with open("../data/pass_text.md") as p_text:
    pass_text = markdown2.markdown(p_text.read())
with open("../data/fail_subject") as f_subject:
    fail_subject = f_subject.read()
with open("../data/fail_text") as f_text:
    fail_text = f_text.read()


def main_thread():
    login = Queue()
    login_to_pre = Queue()
    pre = Queue()
    new_param = {
        "admin_info": {"id": secrets["ADMIN_ID"], "password": secrets["ADMIN_PASSWORD"]},
        "univ_code": secrets["ADMIN_ID"].split("@")[0]
    }
    login.put(new_param)

    login_filter = LoginFilter(login, login_to_pre)
    pre_parse_filter = PreParseFilter(login_to_pre, pre)
    pre_parse_filter.daemon = True

    login_filter.start()
    pre_parse_filter.start()
    login_filter.join()

    if not login_filter.success:
        import sys
        sys.exit(1)

    pks = pre.get()
    with ProcessPool() as main_pool:
        with yaspin(Spinners.dots4, text="Parse applicant's page and export data...", color="yellow", timer=True) as sp:
            applicants = main_pool.map(multi_processing, pks)
            sp.text = "Crawling complete..."
            sp.ok("🦁")

    with yaspin(Spinners.dots4, text="Gathering applicant's data to excel...", color="yellow", timer=True) as sp:
        gathering_applicant_data(applicants)
        sp.text = "Gathering complete..."
        sp.ok("🦁")


def multi_processing(param):
    request = Queue()
    request.put(param)
    request_to_parser = Queue()
    parser_to_export = Queue()
    export_to_sink = Queue()
    sink = Queue()

    request_application_page_filter = RequestApplicantPageFilter(request, request_to_parser)
    parser_filter = ApplicantPageParseFilter(request_to_parser, parser_to_export)
    export_filter = ExportFilter(parser_to_export, export_to_sink)
    sink_filter = ApplicantSinkFilter(export_to_sink, sink)

    request_application_page_filter.start()
    parser_filter.start()
    export_filter.start()
    sink_filter.start()

    return sink.get()
    # TODO: 2021/03/06 분석 필터 추가하기


if __name__ == '__main__':
    import sys
    sys.setrecursionlimit(3000)
    required_dir = Path("../지원자 서류")
    required_dir2 = Path("../applicant")
    if not required_dir.exists():
        required_dir.mkdir()
    if not required_dir2.exists():
        required_dir2.mkdir()

    while True:
        print("0. 종료 1. 크롤링 2. 정보 복원 3. 합격 처리 4. 메일 발송")
        menu = input("메뉴 선택: ")
        if menu == "0":
            break
        elif menu == "1":
            main_thread()
        elif menu == "2":
            print(unpickle_applicant(input("이름: ")))
        elif menu == "3":
            input_names = input("합격자들 (공백으로 구분): ").split()
            restored = unpickle_all_applicant()
            for applicant in restored:
                if applicant.name in input_names:
                    applicant.is_pass = True
                    pickle_applicant(applicant)
            gathering_applicant_data(restored)
        elif menu == "4":
            restored = unpickle_all_applicant()
            for applicant in restored:
                send_email_to_applicant(applicant, applicant.is_pass)




