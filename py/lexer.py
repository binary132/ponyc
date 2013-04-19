import re
import sys
import ply.lex
from ply.lex import TOKEN

class Lexer(object):
  """
  A lexer for the Pony language.
  """

  def __init__(self, error_func):
    self.lexer = None
    self.error_func = error_func
    self.nesting = 0

  def build(self, **kwargs):
    self.lexer = ply.lex.lex(object=self, **kwargs)

  def reset(self):
    self.lexer.lineno = 1

  def input(self, text):
    self.lexer.input(text)

  def token(self):
    return self.lexer.token()

  def column(self, pos):
    last_nl = self.lexer.lexdata.rfind('\n', 0, pos)
    if last_nl < 0:
      last_nl = 0
    column = pos - last_nl
    return column

  # Private

  def _error(self, msg, token):
    self.error_func(token.lineno, self.column(token.lexpos), msg)
    self.lexer.skip(1)

  # State for nested comments
  states = [
    ('nested', 'exclusive')
    ]

  # Keywords

  keywords = (
    'USE', 'ACTOR', 'CLASS', 'TRAIT', 'TYPE', 'IS',
    'VAR', 'VAL', 'DEF', 'MSG', 'PRIVATE',
    'IF', 'THEN', 'ELSE', 'MATCH', 'AS', 'WHILE', 'DO', 'FOR', 'IN',
    'REFLECT', 'ABSORB', 'FIELD', 'METHOD', 'THIS', 'TRUE', 'FALSE',
    'AND', 'OR', 'XOR', 'NOT'
    )

  keyword_map = {}
  for keyword in keywords:
    keyword_map[keyword.lower()] = keyword

  # Symbols

  tokens = keywords + (
    'ID', 'INT', 'FLOAT', 'STRING',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'LSHIFT', 'RSHIFT',
    'LT', 'LE', 'EQ', 'NE', 'GE', 'GT',
    'EQUALS', 'COMMA', 'DOT', 'SEMI', 'COLON',
    'LPAREN', 'RPAREN',
    'LBRACKET', 'RBRACKET',
    'LBRACE', 'RBRACE',
    'CASE', 'PARTIAL'
    )

  t_PLUS = r'\+'
  t_MINUS = r'-'
  t_TIMES = r'\*'
  t_DIVIDE = r'/'
  t_MOD = r'%'
  t_LSHIFT = r'<<'
  t_RSHIFT = r'>>'
  t_LT = r'<'
  t_LE = r'<='
  t_EQ = r'=='
  t_NE = r'<>'
  t_GE = r'>='
  t_GT = r'>'
  t_EQUALS = r'='
  t_COMMA = r','
  t_DOT = r'\.'
  t_SEMI = r';'
  t_COLON = r':'
  t_LPAREN = r'\('
  t_RPAREN = r'\)'
  t_LBRACKET = r'\['
  t_RBRACKET = r'\]'
  t_LBRACE = r'\{'
  t_RBRACE = r'\}'
  t_CASE = r'\|'
  t_PARTIAL = r'\\'

  t_ignore = ' \t'
  t_nested_ignore = ''

  hex_dig = r'[0-9a-fA-F]'
  esc_seq = r'[abfnrtv"\\0]'
  esc_hex = r'x'+hex_dig+hex_dig
  esc_uni = r'u'+hex_dig+hex_dig+hex_dig+hex_dig
  esc_uni2 = r'U'+hex_dig+hex_dig+hex_dig+hex_dig+hex_dig+hex_dig
  esc = r'\\('+esc_seq+'|'+esc_hex+'|'+esc_uni+'|'+esc_uni2+')'

  def t_nested_begin(self, t):
    r'/\*'
    self.nesting += 1

  def t_nested_end(self, t):
    r'\*/'
    self.nesting -= 1
    if self.nesting == 0:
      t.lexer.begin('INITIAL')

  def t_nested_comment(self, t):
    r'([^/*]|\*[^/]|/[^*])+'
    t.lexer.lineno += t.value.count('\n')

  def t_nested_error(self, t):
    pass

  @TOKEN(r'"('+esc+r'|[^\\"])*"')
  def t_STRING(self, t):
    t.lexer.lineno += t.value.count('\n')
    return t

  def t_BAD_STRING(self, t):
    r'"[^"]*"'
    t.lexer.lineno += t.value.count('\n')
    msg = "String contains invalid escape sequence"
    self._error(msg, t)

  def t_FLOAT(self, t):
    r'[0-9]+\.[0-9]+([eE][-+]?[0-9]+)?'
    t.value = float(t.value)
    return t

  def t_HEXINT(self, t):
    r'0x[_0-9a-fA-F]+'
    t.value = t.value.replace('_', '')
    t.value = int(t.value, 16)
    t.type = 'INT'
    return t

  def t_OCTINT(self, t):
    r'0[_0-7]+'
    t.value = t.value.replace('_', '')
    t.value = int(t.value, 8)
    t.type = 'INT'
    return t

  def t_BININT(self, t):
    r'0b[_0-1]+'
    t.value = t.value.replace('_', '')
    t.value = int(t.value, 2)
    t.type = 'INT'
    return t

  def t_INT(self, t):
    r'[1-9][_0-9]*'
    t.value = t.value.replace('_', '')
    t.value = int(t.value)
    return t

  def t_ID(self, t):
    r'[_a-zA-Z][_a-zA-Z0-9]*'
    t.type = self.keyword_map.get(t.value, "ID")
    return t

  def t_linecomment(self, t):
    r'//[^\n]*'

  def t_blockcomment(self, t):
    r'/\*'
    self.nesting += 1
    t.lexer.begin('nested')

  def t_newline(self, t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')

  def t_error(self, t):
    msg = 'Unrecognized character %s' % repr(t.value[0])
    self._error(msg, t)