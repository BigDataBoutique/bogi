import json


class HttpClient:
    def __init__(self):
        setattr(self, 'assert', self._assert)
        setattr(self, 'global', Variables())

    """
    Creates test with name 'testName' and body 'func'.
    All tests will be executed right after response handler script.
    """
    def test(self, testName, func):
        func()

    """
    Checks that condition is true and throw an exception otherwise.
    @param condition
    @param message if specified it will be used as an exception message.
    """
    def _assert(self, condition, error_message=None):
        if not condition:
            raise Exception(error_message)

    """
    Prints text to the response handler or test stdout and then terminates the line.
    """
    def log(self, text):
        print(text)
        print('\n')


class HttpResponse:
    def __init__(self, response):
        self.status = response.status_code
        self.body = ResponseBody(response)
        self.headers = response.headers
        self.contentType = {
            'mimeType': (response.headers.get('Content-Type') or '').split('; charset')[0],
            'charset': response.encoding
        }


class ResponseBody:
    def __init__(self, response):
        self.headers = response.headers
        self.json = None
        try:
            self.json = response.json()
        except json.decoder.JSONDecodeError as e:
            pass

    def hasOwnProperty(self, val):
        if val == 'headers':
            return True

        return False


class Variables:
    def __init__(self):
        self.dict = dict()

    def set(self, varName, varValue):
        self.dict[varName] = varValue

    def get(self, varName):
        self.dict.get(varName)

    def isEmpty(self):
        return len(self.dict) == 0

    def clear(self, varName):
        if varName in self.dict:
            del self.dict[varName]

    def clearAll(self):
        self.dict.clear()
