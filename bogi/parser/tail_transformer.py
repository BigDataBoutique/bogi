from collections import namedtuple

from lark import Tree, Token

from bogi.parser.util import BaseTransformer, Header

RequestTail = namedtuple('RequestTail', ['message_body', 'response_handler', 'response_ref'])
MessageBody = namedtuple('MessageBody', ['messages'])
ContentLine = namedtuple('ContentLine', ['content'])
InputFileRef = namedtuple('InputFileRef', ['path'])
MultipartField = namedtuple('MultipartField', ['headers', 'messages'])
ResponseHandler = namedtuple('ResponseHandler', ['script', 'path'])
ResponseReference = namedtuple('ResponseReference', ['path'])


class TailTransformer(BaseTransformer):

    def request_tail(self, parts):
        message_body = None
        response_handler = None
        response_reference = None

        for p in parts:
            if type(p) is MessageBody:
                message_body = p
            if type(p) is ResponseHandler:
                response_handler = p
            if type(p) is ResponseReference:
                response_reference = p
        return RequestTail(message_body=message_body,
                           response_handler=response_handler,
                           response_ref=response_reference)

    def message_body(self, parts):
        messages = []
        for p in parts:
            if type(p) is list:
                messages += p
        return MessageBody(messages)

    def messages(self, parts):
        message_lines = []
        for p in parts:
            if type(p) in [ContentLine, InputFileRef]:
                message_lines.append(p)
            elif type(p) is list:
                message_lines += self.messages(p)
        return message_lines

    def content_line(self, parts):
        return ContentLine(self._join_parts(parts))

    def input_file_ref(self, parts):
        file_path = self._filter_type(parts, Tree)[0]
        for ch in file_path.children:
            if type(ch) is Token and ch.type == 'FILE_PATH_STR':
                file_path = str(ch)
                break
        return InputFileRef(file_path)

    def multipart_form_data(self, parts):
        return [p for p in parts if type(p) is MultipartField]

    def multipart_field(self, parts):
        headers = [p for p in parts if type(p) is Header]
        messages = []
        for p in parts:
            if type(p) is list:
                messages += p
        return MultipartField(headers=headers, messages=messages)

    def response_handler(self, parts):
        script_path, script_code = None, None
        for p in parts:
            if type(p) is Token and p.type == 'HANDLER_SCRIPT':
                return ResponseHandler(script=str(p).strip(), path=None)

            elif type(p) is Tree and p.data == 'file_path':
                return ResponseHandler(script=None, path=self._join_parts(p.children))

    def response_ref(self, parts):
        for p in parts:
            if type(p) is Tree and p.data == 'file_path':
                return ResponseReference(path=self._join_parts(p.children).strip())
