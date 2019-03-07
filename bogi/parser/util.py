import os
import re
from collections import namedtuple

from lark import Transformer, Tree

HeaderList = namedtuple('HeaderList', ['headers'])
Header = namedtuple('Header', ['field', 'value'])

class BaseTransformer(Transformer):

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

    def _filter_type(self, parts, cls):
        return [p for p in parts if type(p) is cls]

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

def load_grammar(parts):
    grammar = []
    dir_path = os.path.dirname(os.path.realpath(__file__))
    for grm in parts:
        grammar_path = os.path.join(dir_path, '../grammar/{}.lark'.format(grm))
        with open(grammar_path, 'r') as f:
            grammar.append(f.read())
    return '\n'.join(grammar)