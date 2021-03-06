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
#     ¡™£¢∞§¶•ªº–≠«``∑´´†¥¨ˆˆøπ“‘åß∂ƒ©˙∆˚¬…æΩ≈ç√∫˜˜≤≥ç


if __name__ == '__main__':
    init = Queue()
    init_to_login = Queue()
    login_to_pre = Queue()
    pre = Queue()

    init.put("../secrets.json")

    init_filter = InitFilter(init, init_to_login)
    login_filter = LoginFilter(init_to_login, login_to_pre)
    pre_parse_filter = PreParseFilter(login_to_pre, pre)

    init_filter.start()
    login_filter.start()
    pre_parse_filter.start()
    pre_parse_filter.join()

    pks = pre.get()
    with ProcessPool() as main_pool:
        main_pool.map(main_processing, pks)






