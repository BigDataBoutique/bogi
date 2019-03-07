from collections import namedtuple
from urllib.parse import urljoin

from lark import Tree, Token

from bogi.parser.util import BaseTransformer, HeaderList

RequestLine = namedtuple('RequestLine', ['method', 'target', 'http_version'])
RequestSeparator = namedtuple('RequestSeparator', ['comment'])

class Request:
    def __init__(self, request_line, headers=None, separators=None, tail=None):
        self.request_line = request_line
        self.separators = separators
        self.headers = headers or []
        self.tail = tail

    @property
    def id(self):
        if not self.separators:
            return None
        return self.separators[-1].comment

    @property
    def method(self):
        return self.request_line.method or 'GET'
    
    @property
    def http_version(self):
        return self.request_line.method

    @property
    def target(self):
        host_headers = [h for h in self.headers if h.field.lower() == 'host']
        if not host_headers:
            return self.request_line.target
        return urljoin(host_headers[0].value, self.request_line.target)

    @property
    def charset(self):
        return self._header_param('content-type', 'charset')

    @property
    def multipart_boundary(self):
        return self._header_param('content-type', 'boundary')

    def _header_param(self, field, param):
        headers = [h for h in self.headers if h.field.lower() == field.lower()]
        for h in headers:
            parts = h.value.split(';')
            for p in parts:
                p = p.split('=')
                if p[0].lower() == param:
                    return p[1]

    def __repr__(self):
        parts = (
            [self.request_line] +
            [h for h in self.headers] +
            [self.tail.message_body, self.tail.response_handler, self.tail.response_ref]
        )
        parts = ['-' + str(p) for p in parts if p is not None]
        req_id = '(' + self.id + ')' if self.id else ''
        return 'Request{}\n'.format(req_id) + '\n'.join(parts)

class MainTransformer(BaseTransformer):

    def requests_file(self, parts):
        parts = self._flatten(parts)
        parts = self._filter_none(parts)

        separators = []
        for p in parts:
            if type(p) is RequestSeparator:
                separators.append(p)
            if type(p) is Request:
                p.separators = separators
                separators = []            
        return self._filter_type(parts, Request)

    def request(self, parts):
        parts = self._filter_none(parts)
        request_line, headers, tail = None, None, None

        for p in parts:
            if type(p) is RequestLine:
                request_line = p
            elif type(p) is HeaderList:
                headers = p.headers
            elif type(p) is Token and p.type == 'REQUEST_TAIL':
                tail = str(p)

        return Request(request_line=request_line, headers=headers, tail=tail)

    def request_separator(self, parts):
        line_tail = self._filter_type(parts, Tree)[0]
        for p in line_tail.children:
            if type(p) is Token and p.type == 'LINE_TAIL_STR':
                return RequestSeparator(str(p).strip())
        return RequestSeparator(comment=None)

    def request_line(self, parts):
        method, target = None, None
        for p in parts:
            if type(p) is Tree:
                if p.data == 'method':
                    method = str(p.children[0])
                elif p.data == 'request_target':
                    target = self._join_parts(p.children)
        return RequestLine(method=method, target=target, http_version=None)

    def _flatten(self, x):
        if isinstance(x, list):
            return [a for i in x for a in self._flatten(i)]
        else:
            return [x]

    absolute_form = BaseTransformer._join_parts
    origin_form = BaseTransformer._join_parts
    path_separator = BaseTransformer._join_parts
    absolute_path = BaseTransformer._join_parts
    query = BaseTransformer._join_replace_whitespace
    fragment = BaseTransformer._join_replace_whitespace
    newline_with_indent = BaseTransformer._none
    request_with_separator = BaseTransformer._filter_none
