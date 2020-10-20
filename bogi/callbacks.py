from bogi import bcolors


class CallbackBase:
    def __init__(self):
        self.successes = []
        self.failures = []

    def failure(self, f):
        self.failures.append(f)

    def success(self, s):
        self.successes.append(s)


class LoggerCallback(CallbackBase):
    def __init__(self, logger):
        super(LoggerCallback, self).__init__()
        self.logger = logger

    def failure(self, f):
        super().failure(f)
        self.logger.error(f'\t{bcolors.FAIL}Check {f.request.method} {f.request.target} failed\n\t'
                          f'{f.error}{bcolors.ENDC}')

    def success(self, s):
        super().success(s)
        self.logger.info(f'\t{bcolors.OKCYAN}Check {s.request.method} {s.request.target} succeeded'
                         f' (latency: {s.latency}ms / response time: {s.response_time}ms){bcolors.ENDC}')
