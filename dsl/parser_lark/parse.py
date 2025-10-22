# parse.py

from __future__ import annotations
import re
from dataclasses import asdict, is_dataclass
from typing import Any
from lark import Lark, Tree, Token
from transform import ASTBuilder
from codegen import CodegenPyContract
from pprint import pprint

GRAMMAR_PATH = "grammar.lark"
START_RULE = "start"

def parse_to_ast(text: str):
    with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
        grammar = f.read()
    parser = Lark(grammar, parser="lalr", start=START_RULE, propagate_positions=True)
    tree = parser.parse(text)
    return ASTBuilder().transform(tree)

def bold_names(text: str, names):
    print('---')
    text = re.sub(r'#.*', '', text)  # drop comments to EOL
    words = sorted({n for n in names if n}, key=len, reverse=True)
    if not words:
        print(text, end=""); return
    pat = r'\b(?:%s)\b' % '|'.join(re.escape(w) for w in words)
    print(re.sub(pat, lambda m: f'\033[1m{m.group(0)}\033[0m', text), end="")
    print('---')

def color_keywords_blue(text: str, names, *, case_sensitive=False, bold=False):
    text = re.sub(r'#.*', '', text)  # drop comments to EOL
    words = sorted({n for n in names if n}, key=len, reverse=True)
    if not words:
        print(text, end=""); return
    pat = r'\b(?:%s)\b' % '|'.join(re.escape(w) for w in words)
    flags = 0 if case_sensitive else re.IGNORECASE
    code = '\033[1;34m' if bold else '\033[34m'   # bold blue or plain blue
    print(re.sub(pat, lambda m: f'{code}{m.group(0)}\033[0m', text, flags=flags), end="")


keywords = {
    "monitor",
    "event",
    "events",
    "initial",
    "state",
    "hot",
    "next",
    "hotnext",
    "always",
    "and",
    "or",
    "seq",
    "not",
    "case",
    "veto",
    "error",
    "ok",
    "include",
    "if",
    "where",
    "ignore",
    "exists",
    "call",
    "assert",
    "okif"
}

if __name__ == "__main__":
    spec_file = "examples/monitor.mon"
    # spec_file = "examples/demo1.mon"
    # spec_file = "examples/demo2.mon"

    with open("grammar.lark") as gfile:
        grammar = gfile.read()

    with open(spec_file) as f:
        source = f.read()

    ast = parse_to_ast(source)
    pprint(ast)
    #color_keywords_blue(source, keywords, bold=True)
    #code = CodegenPyContract().translate(ast)
    # print(code)
