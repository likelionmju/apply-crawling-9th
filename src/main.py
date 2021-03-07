from pathlib import Path

from filters import *
from queue import Queue
from pathos.multiprocessing import ProcessPool


def main_thread():
    init = Queue()
    init_to_login = Queue()
    login_to_pre = Queue()
    pre = Queue()
    init.put("../secrets.json")

    init_filter = InitFilter(init, init_to_login)
    login_filter = LoginFilter(init_to_login, login_to_pre)
    pre_parse_filter = PreParseFilter(login_to_pre, pre)
    pre_parse_filter.daemon = True

    init_filter.start()
    login_filter.start()
    pre_parse_filter.start()
    login_filter.join()

    if not login_filter.success:
        import sys
        sys.exit(1)

    pks = pre.get()
    with ProcessPool() as main_pool:
        with yaspin(Spinners.dots4, text="Parse applicant's page and export data...", color="yellow", timer=True) as sp:
            main_pool.map(multi_processing, pks)
            sp.text = "Crawling complete..."
            sp.ok("🦁")


def multi_processing(param):
    request = Queue()
    request.put(param)
    request_to_parser = Queue()
    parser_to_export = Queue()
    export_to_sink = Queue()

    request_application_page_filter = RequestApplicantPageFilter(request, request_to_parser)
    parser_filter = ApplicantPageParseFilter(request_to_parser, parser_to_export)
    export_filter = ExportFilter(parser_to_export, export_to_sink)
    sink_filter = ApplicantSinkFilter(export_to_sink, Queue())

    request_application_page_filter.start()
    parser_filter.start()
    export_filter.start()
    sink_filter.start()
    sink_filter.join()
    # TODO: 2021/03/06 분석 필터 추가하기


def recover_applicant_info(name: str):
    from crawler import unpickle_applicant
    print(unpickle_applicant(name))


if __name__ == '__main__':
    import sys
    sys.setrecursionlimit(3000)
    required_dir = Path("../지원자 서류")
    required_dir2 = Path("../applicant")
    if not required_dir.exists():
        required_dir.mkdir()
    if not required_dir2.exists():
        required_dir2.mkdir()

    menu = input("1. 크롤링 2. 정보 복원\r\n메뉴 선택: ")
    if menu == "1":
        main_thread()
    elif menu == "2":
        input_name = input("이름: ")
        recover_applicant_info(input_name)








