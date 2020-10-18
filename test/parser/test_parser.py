import unittest

from bogi.parser.main import Parser
from bogi.parser.main_transformer import RequestSeparator
from bogi.parser.tail_transformer import MessageBody, RequestTail, ContentLine, Header, ResponseHandler, ResponseReference
from test.utils import dedent


class ParserTests(unittest.TestCase):

    def setUp(self):
        self.parser = Parser()

    def test_simple(self):
        reqs = self.parser.parse(dedent('''
        ### Post to API add
        ### post-to-api
        POST http://example.com/api/a/b/c/
        Content-Type: application/json
        From: origin@example.com
        '''))

        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].id, 'post-to-api')
        self.assertEqual(reqs[0].method, 'POST')
        self.assertEqual(reqs[0].target, 'http://example.com/api/a/b/c/')
        self.assertEqual(len(reqs[0].headers), 2)
        self.assertEqual(reqs[0].headers[0], Header('Content-Type', 'application/json'))
        self.assertEqual(reqs[0].headers[1], Header('From', 'origin@example.com'))

    def test_localhost_port(self):
        reqs = self.parser.parse(dedent('''
        POST http://localhost:3000/api/a/b/c/
        '''))

        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].method, 'POST')
        self.assertEqual(reqs[0].target, 'http://localhost:3000/api/a/b/c/')

    def test_no_final_newline(self):
        reqs = self.parser.parse('POST http://example.com/api/a/b/c')
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].method, 'POST')
        self.assertEqual(reqs[0].target, 'http://example.com/api/a/b/c')

    def test_newlines(self):
        reqs = self.parser.parse(dedent('''
        
        
        ###
        
        POST http://example.com/api/a/b/c
         
        ###
        ###
        ###
        
        POST http://example.com/api/a/b/c
        
        ### 
        
        ###
        
        
        
        '''))

        self.assertEqual(len(reqs), 2)

    def test_multiple_requests(self):
        reqs = self.parser.parse(dedent('''
        ### First
        GET http://example.com
        ### Second
        POST http://example.com
        ###
        ### Third
        /api/test
        Host: example.com
        ###
        ###
        '''))

        self.assertEqual(len(reqs), 3)
        self.assertEqual(reqs[0].method, 'GET')
        self.assertEqual(reqs[0].separators, [RequestSeparator('First')])
        self.assertEqual(reqs[0].target, 'http://example.com')
        self.assertEqual(reqs[1].method, 'POST')
        self.assertEqual(reqs[1].separators, [RequestSeparator('Second')])
        self.assertEqual(reqs[1].target, 'http://example.com')
        self.assertEqual(reqs[2].method, 'GET')
        self.assertEqual(reqs[2].separators, [RequestSeparator(None), RequestSeparator('Third')])
        self.assertEqual(reqs[2].target, '/api/test')
        self.assertEqual(reqs[2].headers[0], Header('Host', 'example.com'))

    def test_origin_form_and_headers(self):
        reqs = self.parser.parse(dedent('''
        PUT /api/a/b/c?a=123&b=456&
                        c=789#foo
        Host: multiline.
                    example.
                    com
        Content-Type:         application/json
        '''))

        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].method, 'PUT')
        self.assertEqual(reqs[0].target, '/api/a/b/c?a=123&b=456&c=789#foo')
        self.assertEqual(reqs[0].headers[0], Header('Host', 'multiline.example.com'))
        self.assertEqual(reqs[0].headers[1], Header('Content-Type', 'application/json'))

    def test_absolute_form(self):
        reqs = self.parser.parse(dedent('''
        ### Post to API add
        POST http://example.com/api/a/b/c
        Content-Type: application/json
        '''))

        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].method, 'POST')
        self.assertEqual(reqs[0].target, 'http://example.com/api/a/b/c')

    def test_request_options(self):
        reqs = self.parser.parse(dedent('''
        // @no-redirect
        ### Post to API add
        POST http://example.com/api/a/b/c
        Content-Type: application/json
        '''))

        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].method, 'POST')
        self.assertEqual(reqs[0].target, 'http://example.com/api/a/b/c')

    def test_simple_with_tail(self):
        reqs = self.parser.parse(dedent('''
        ### Post to API add
        POST http://example.com/api/a/b/c
        Content-Type: application/json
        From: origin@example.com

        {
            "name": "entity",
            "value": "content"
        }
        > {%
        if (resp.status === 200) {
            resolve();
        }
        %}
        <> ./path/response.ref.json
        '''))

        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].method, 'POST')
        self.assertEqual(reqs[0].target, 'http://example.com/api/a/b/c')
        self.assertEqual(len(reqs[0].headers), 2)
        self.assertEqual(reqs[0].headers[0], Header('Content-Type', 'application/json'))
        self.assertEqual(reqs[0].headers[1], Header('From', 'origin@example.com'))
        self.assertEqual(reqs[0].tail, RequestTail(
            message_body=MessageBody([
                ContentLine('{'),
                ContentLine('    "name": "entity",'),
                ContentLine('    "value": "content"'),
                ContentLine('}')
            ]),
            response_handler=ResponseHandler(
                script=dedent('''
                if (resp.status === 200) {
                    resolve();
                }
                ''').strip(),
                path=None,
                expected_status_code=None
            ),
            response_ref=ResponseReference(path='./path/response.ref.json')
        ))

    def test_multiple_requests_with_tail(self):
        reqs = self.parser.parse(dedent('''
        ### Post to API add
        GET http://example.com/api/a/b/c
        Content-Type: application/json
        From: origin@example.com

        {
            "name": "entity",
            "value": "content"
        }
        > {%
        if (resp.status === 200) {
            resolve();
        }
        %}
        <> ./path/response.ref.json
        ###
        ###
        ### Post to API add
        POST http://example.com/api/a/b/c
        Content-Type: application/json
        From: origin@example.com

        {
            "name": "entity",
            "value": "content"
        }
        > {%
        if (resp.status === 200) {
            resolve();
        }
        %}
        <> ./path/response.ref.json
        '''))

        self.assertEqual(len(reqs), 2)

        self.assertEqual(reqs[0].method, 'GET')
        self.assertEqual(reqs[0].target, 'http://example.com/api/a/b/c')
        self.assertEqual(len(reqs[0].headers), 2)
        self.assertEqual(reqs[0].headers[0], Header('Content-Type', 'application/json'))
        self.assertEqual(reqs[0].headers[1], Header('From', 'origin@example.com'))
        self.assertEqual(reqs[0].tail, RequestTail(
            message_body=MessageBody([
                ContentLine('{'),
                ContentLine('    "name": "entity",'),
                ContentLine('    "value": "content"'),
                ContentLine('}')
            ]),
            response_handler=ResponseHandler(
                script=dedent('''
                if (resp.status === 200) {
                    resolve();
                }
                ''').strip(),
                path=None,
                expected_status_code=None
            ),
            response_ref=ResponseReference(path='./path/response.ref.json')
        ))

        self.assertEqual(reqs[1].method, 'POST')
        self.assertEqual(reqs[1].target, 'http://example.com/api/a/b/c')
        self.assertEqual(len(reqs[1].headers), 2)
        self.assertEqual(reqs[1].headers[0], Header('Content-Type', 'application/json'))
        self.assertEqual(reqs[1].headers[1], Header('From', 'origin@example.com'))
        self.assertEqual(reqs[1].tail, RequestTail(
            message_body=MessageBody([
                ContentLine('{'),
                ContentLine('    "name": "entity",'),
                ContentLine('    "value": "content"'),
                ContentLine('}')
            ]),
            response_handler=ResponseHandler(
                script=dedent('''
                if (resp.status === 200) {
                    resolve();
                }
                ''').strip(),
                path=None,
                expected_status_code=None
            ),
            response_ref=ResponseReference(path='./path/response.ref.json')
        ))
