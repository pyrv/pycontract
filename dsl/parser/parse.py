# parse.py
from lark import Lark

if __name__ == "__main__":
    with open("grammar.lark") as gfile:
        grammar = gfile.read()

    with open("monitor.mon") as f:
        source = f.read()
        print(repr(source))

    parser = Lark(grammar, parser="lalr", start="start")
    tree = parser.parse(source)
    print(tree.pretty())
