import unittest

from bogi.parser import Parser, Header
from utils import dedent

class ParserTests(unittest.TestCase):

    def setUp(self):
        self.parser = Parser()

    def test_simple(self):
        reqs = self.parser.parse(dedent('''
        ### Post to API add
        POST http://example.com/api/a/b/c
        Content-Type: application/json
        From: origin@example.com
        '''))

        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0].method, 'POST')
        self.assertEqual(reqs[0].target, 'http://example.com/api/a/b/c')
        self.assertEqual(len(reqs[0].headers), 2)
        self.assertEqual(reqs[0].headers[0], Header('Content-Type', 'application/json'))
        self.assertEqual(reqs[0].headers[1], Header('From', 'origin@example.com'))

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
        self.assertEqual(reqs[0].target, 'http://example.com')
        self.assertEqual(reqs[1].method, 'POST')
        self.assertEqual(reqs[1].target, 'http://example.com')
        self.assertEqual(reqs[2].method, 'GET')
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
