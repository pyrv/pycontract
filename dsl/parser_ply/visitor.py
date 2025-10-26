# visitor.py
from __future__ import annotations
from dataclasses import is_dataclass, fields
from typing import Any, Iterable

# ---- tiny generic visitor base ----

class Visitor:
    def visit(self, node: Any):
        if node is None:
            return
        meth = getattr(self, "visit_" + node.__class__.__name__, None)
        if meth is not None:
            return meth(node)
        return self.generic_visit(node)

    def generic_visit(self, node: Any):
        # default: walk dataclass fields and lists
        if is_dataclass(node):
            for f in fields(node):
                self.visit(getattr(node, f.name))
        elif isinstance(node, list):
            for x in node: self.visit(x)
        else:
            # leaf (str/int/enum/None): ignore
            pass

# ---- the simplest printer ----

class PrintVisitor(Visitor):
    def __init__(self):
        self.indent = 0

    def line(self, text: str):
        print("  " * self.indent + text)

    # catch-all that prints the node class name, then walks children
    def generic_visit(self, node: Any):
        from dataclasses import is_dataclass, fields
        if is_dataclass(node):
            self.line(node.__class__.__name__)
            self.indent += 1
            for f in fields(node):
                val = getattr(node, f.name)
                # show field name briefly
                self.line(f"- {f.name}:")
                self.indent += 1
                super().generic_visit(val)
                self.indent -= 1
            self.indent -= 1
        elif isinstance(node, list):
            self.line("[list]")
            self.indent += 1
            for x in node: self.visit(x)
            self.indent -= 1
        else:
            # leaves
            self.line(repr(node))

    # (optionally add a special case to show EventSpec prefix nicely)
    def visit_EventSpec(self, node):
        # print a one-liner, then descend
        pref = node.prefix.value if node.prefix is not None else None
        self.line(f"EventSpec(prefix={pref})")
        self.indent += 1
        self.visit(node.pat)
        self.indent -= 1
