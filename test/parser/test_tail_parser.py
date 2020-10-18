import unittest
from test.utils import dedent

from bogi.parser.tail import TailParser
from bogi.parser.tail_transformer import MessageBody, ContentLine, InputFileRef, MultipartField, Header, ResponseHandler, ResponseReference

class TailParserTests(unittest.TestCase):

    def test_content_lines(self):
        body = dedent('''
        {
            "foo": "bar",
            "param2": "value2"
        }''')

        tail = TailParser().parse(body)

        self.assertEqual(tail.message_body, MessageBody([
            ContentLine('{'),
            ContentLine('    "foo": "bar",'),
            ContentLine('    "param2": "value2"'),
            ContentLine('}')
        ]))

    def test_file_refs(self):
        body = dedent('''
        < body.json
        < /home/file''')

        tail = TailParser().parse(body)
        self.assertEqual(tail.message_body, MessageBody([
            InputFileRef('body.json'),
            InputFileRef('/home/file')
        ]))

    def test_message_body(self):
        body = dedent('''
        {
            "key": "val"
        }
        < body.json
        < /home/file
        testing''')

        tail = TailParser().parse(body)
        self.assertEqual(tail.message_body, MessageBody([
            ContentLine('{'),
            ContentLine('    "key": "val"'),
            ContentLine('}'),
            InputFileRef('body.json'),
            InputFileRef('/home/file'),
            ContentLine('testing')
        ]))

    def test_multipart(self):
        body = dedent('''
        --abcd
        Content-Disposition: form-data; name="text"

        Text
        --abcd
        Content-Disposition: form-data; name="file_to_send"; filename="input.txt"

        < ./input.txt
        --abcd--''')

        tail = TailParser(multipart_boundary='abcd').parse(body)
        self.assertEqual(tail.message_body, MessageBody([
            MultipartField(
                headers=[Header(field='Content-Disposition', value='form-data; name="text"')],
                messages=[ContentLine(content='Text')]),
            MultipartField(
                headers=[Header(field='Content-Disposition', value='form-data; name="file_to_send"; filename="input.txt"')],
                messages=[InputFileRef(path='./input.txt')])
        ]))

    def test_response_handler_script(self):
        script = dedent('''
        console.log('Multiline script');
        client.global.set("auth", response.body.token);
        ''')
        body = dedent('''
        > {% ''' + script + ''' %}''')

        tail = TailParser().parse(body)
        self.assertEqual(tail.response_handler, ResponseHandler(script=script.strip(), path=None))

    def test_response_handler_path(self):
        body = dedent('''
        > ./script.js''')

        tail = TailParser().parse(body)
        self.assertEqual(tail.response_handler, ResponseHandler(script=None, path='./script.js'))

    def test_response_status_code(self):
        body = dedent('''
        >STATUS 301''')

        tail = TailParser().parse(body)
        self.assertEqual(tail.response_handler, ResponseHandler(script=None, path=None, expected_status_code=301))

    def test_response_ref(self):
        body = dedent('''
        <> ./previous-response.200.json''')

        tail = TailParser().parse(body)
        self.assertEqual(tail.response_ref, ResponseReference(path='./previous-response.200.json'))
