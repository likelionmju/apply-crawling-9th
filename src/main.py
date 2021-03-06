from pathlib import Path

from filters import *
from queue import Queue
from pathos.multiprocessing import ProcessPool


def main_processing(param):
    request = Queue()
    request.put(param)
    request_to_parser = Queue()
    parser_to_exit = Queue()

    request_application_page_filter = RequestApplicantPageFilter(request, request_to_parser)
    parser_filter = ApplicantPageParseFilter(request_to_parser, parser_to_exit)
    exit_filter = ExitFilter(parser_to_exit, Queue())

    request_application_page_filter.start()
    parser_filter.start()
    exit_filter.start()
    exit_filter.join()
    # TODO: 2021/03/06 분석 필터 추가하기


if __name__ == '__main__':
    required_dir = Path("./지원자 서류")
    if not required_dir.exists():
        required_dir.mkdir()

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
            main_pool.map(main_processing, pks)
            sp.text = "Crawling complete..."
            sp.ok("🦁")






