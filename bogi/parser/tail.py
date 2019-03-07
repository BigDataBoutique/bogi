from lark import Lark

from bogi.parser.tail_transformer import TailTransformer
from bogi.parser.util import load_grammar


class TailParser:

    def __init__(self, multipart_boundary=None):
        self._grammar = load_grammar(['request_tail', 'shared'])
        content_line_token = 'CONTENT_LINE: /(?!(###|< |> |<> {}))[^\\n\\r]+/'

        generated = []

        if multipart_boundary:
            generated.append('BOUNDARY: "{}"'.format(multipart_boundary))
            generated.append(content_line_token.format('|--' + multipart_boundary))
        else:            
            # add dummy token which matches nothing
            generated.append('BOUNDARY: /(?=a)b/')
            generated.append(content_line_token.format(''))

        self._grammar = self._grammar + '\n' + '\n'.join(generated)

    def parse(self, code):
        parser = Lark(self._grammar, start='request_tail', keep_all_tokens=True)
        tree = parser.parse(code)
        return TailTransformer().transform(tree)
