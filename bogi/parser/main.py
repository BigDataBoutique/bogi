from lark import Lark

from bogi.parser.main_transformer import MainTransformer
from bogi.parser.tail_transformer import RequestTail
from bogi.parser.tail import TailParser
from bogi.parser.util import load_grammar


class Parser:

    def __init__(self):
        self._grammar = load_grammar(['main', 'shared'])

    def parse(self, code):
        parser = Lark(self._grammar, start='requests_file', keep_all_tokens=True)
        tree = parser.parse(code + '\n')
        requests = MainTransformer().transform(tree)
        
        for r in requests:
            if r.tail is None:
                r.tail = RequestTail(message_body=None, response_handler=None, response_ref=None)
            else:
                r.tail = TailParser(r.multipart_boundary).parse(r.tail)

        return requests
