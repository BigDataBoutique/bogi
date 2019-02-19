import os
import re
from lark import Lark, Transformer, Tree, Token
from collections import namedtuple

RequestLine = namedtuple('RequestLine', ['method', 'target', 'http_version'])
HeaderList = namedtuple('HeaderList', ['headers'])
Header = namedtuple('Header', ['field', 'value'])

class Request:
    def __init__(self, request_line, headers=None):
        self.method = request_line.method or 'GET'
        self.target = request_line.target
        self.http_version = request_line.http_version
        self.headers = headers or []

    def __repr__(self):
        req_line = RequestLine(self.method, self.target, self.http_version)
        return 'Request\n' + '\n'.join(['-' + str(req_line)] + ['-' + str(h) for h in self.headers])

class RequestTransformer(Transformer):

    def requests_file(self, parts):
        return self._filter_none(parts)

    def request(self, parts):
        parts = self._filter_none(parts)
        request_line, headers = None, None
        
        for p in parts:
            if type(p) is RequestLine:
                request_line = p
            elif type(p) is HeaderList:
                headers = p.headers

        return Request(request_line=request_line, headers=headers)

    def request_with_separator(self, parts):
        filtered = self._filter_none(parts)
        if filtered:
            return filtered[0]

    def request_line(self, parts):
        method, target = None, None
        for p in parts:
            if type(p) is Tree:
                if p.data == 'method':
                    method = str(p.children[0])
                elif p.data == 'request_target':
                    target = self._join_parts(p.children)
        return RequestLine(method=method, target=target, http_version=None)

    def headers(self, parts):
        return HeaderList([p for p in parts if type(p) is Header])

    def header_field(self, parts):
        field, value = None, None
        for p in parts:
            if type(p) is Tree:
                if p.data == 'field_name':
                    field = self._join_parts(p.children)
                elif p.data == 'field_value':
                    value = self._join_parts(p.children).strip()
        return Header(field=field, value=value)


    def _none(self, parts):
        return None

    def _filter_none(self, parts):
        return [p for p in parts if p is not None]

    def _join_parts(self, parts):
        parts = [
            self._join_parts(p.children) if type(p) is Tree else p
            for p in parts
            if p is not None
        ]
        return ''.join([str(p) for p in parts])

    def _join_replace_whitespace(self, parts):
        return re.sub(r'\s', '', self._join_parts(parts))

    absolute_form = _join_parts
    origin_form = _join_parts
    path_separator = _join_parts
    absolute_path = _join_parts
    query = _join_replace_whitespace
    fragment = _join_replace_whitespace
    newline_with_indent = _none
    request_separator = _none


class Parser:

    def __init__(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        grammar_path = os.path.join(dir_path, 'grammar.lark')
        with open(grammar_path, 'r') as f:
            self._lark_parser = Lark(f.read(), start='requests_file', keep_all_tokens=True)

    def parse(self, code):
        tree = self._lark_parser.parse(code)
        requests = RequestTransformer().transform(tree)
        return requests
