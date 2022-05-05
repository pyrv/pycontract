
from pycontract import *
import unittest
import test.utest
from typing import List

import ast

"""
Auction. This is test 5 - but here experimenting with extracting 
information from the code using AST extraction.  
See https://docs.python.org/3/library/ast.html
for documentation of the AST. This documentation does not cover
patterns for Python 3.10. Below we are trying to see of the
software can extract patterns.
"""


@data
class List(Event):
    item: str
    reserve: int


@data
class Bid(Event):
    item: str
    amount: int


@data
class Sell(Event):
    item: str


class Auction(Monitor):
    """
    Consider an Auction Bidding property of an auction bidding site. An item is
    initially listed with a reserve (minimal sales) price, unknown to bidders. The
    initial bidding price is assumed to be 0 dollars, and bids must be strictly
    increasing. At some point the item can be sold if the sales price is strictly
    bigger than the reserve price.
    """

    @initial
    class Always(AlwaysState):
        def transition(self, event):
            match event:
                case List(item, reserve):
                    return self.Listed(item, reserve, 0)

    @data
    class Listed(State):
        item: str
        reserve: int
        prev_bid: int

        def transition(self, event):
            match event:
                case Bid(self.item, amount) if amount > self.prev_bid:
                    return self.Listed(self.item, self.reserve, amount)
                case Bid(self.item, amount) if amount <= self.prev_bid:
                    return error(f'bid {amount} for item {self.item} is not above {self.prev_bid}')
                case Sell(self.item) if self.prev_bid > self.reserve:
                    return ok
                case Sell(self.item) if self.prev_bid <= self.reserve:
                    return error(f'item {self.item} sold below reserve {self.reserve}')


############
# ANALYSIS #
############

def extends_monitor(bases) -> bool:
    return 'Monitor' in bases


def extends_state(bases) -> bool:
    for base in bases:
        if base in ['State', 'AlwaysState', 'HotState', 'NextState', 'HotNextState', 'AlwaysNextState']:
            return True
    return False


class Analyzer(ast.NodeVisitor):
    """
    The AST visitor.
    """
    def __init__(self):
        pass

    def visit_ClassDef(self, node):
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        if 'Monitor' in bases:
            print(f'Monitor {node.name}:')
            self.generic_visit(node)
        if extends_state(bases):
            print(f'  State {node.name}:')
            self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name == 'transition':
            for stmt in node.body:
                #print(f'    {ast.dump(stmt)}')
                match stmt:
                    case ast.Match(subject, cases):
                        print(f'    {subject.id}')
                        for acase in cases:
                            match acase:
                                case ast.match_case(pattern, guard, body):
                                    match pattern:
                                        case ast.MatchClass(cls, patterns, _, _):
                                            print(f'      {cls.id}')
                                            for pat in patterns:
                                                print(f'        {ast.dump(pat)}')
                                case _:
                                    print('      no match')





def analyze(monitor_file: str ):
    with open(monitor_file, "r") as source:
        tree = ast.parse(source.read())
        analyzer = Analyzer()
        analyzer.visit(tree)


class Test1(test.utest.Test):
    def test1(self):
        analyze(__file__)

        """
        This will print:
        
        Monitor Auction:
          State Always:
            event
              List
                MatchAs(name='item')
                MatchAs(name='reserve')
              State Listed:
                event
                  Bid
                    MatchValue(value=Attribute(value=Name(id='self', ctx=Load()), attr='item', ctx=Load()))
                    MatchAs(name='amount')
                  Bid
                    MatchValue(value=Attribute(value=Name(id='self', ctx=Load()), attr='item', ctx=Load()))
                    MatchAs(name='amount')
                  Sell
                    MatchValue(value=Attribute(value=Name(id='self', ctx=Load()), attr='item', ctx=Load()))
                  Sell
                    MatchValue(value=Attribute(value=Name(id='self', ctx=Load()), attr='item', ctx=Load()))
                    
        So it is possible to obtain the AST from a Python 3.10 program, including the AST for the patterns.
        """


if __name__ == '__main__':
    unittest.main()

"""
This is what the AST looks like for the match statement of this 
statement:

            match event:
                case List(item, reserve):
                    return self.Listed(item, reserve, 0)


Match(
  subject=Name(id='event', ctx=Load()), 
  cases=[
    match_case(
        pattern=MatchClass(
            cls=Name(id='List', ctx=Load()),
            patterns=[
                MatchAs(name='item'), 
                MatchAs(name='reserve')
            ], 
            kwd_attrs=[],
            kwd_patterns=[]
        ), 
        guard=Constant(value=True), 
        body=[
            Return(
                value=Call(
                          func=Attribute(value=Name(id='self', ctx=Load()), 
                          attr='Listed', ctx=Load()),
                          args=[
                              Name(id='item', ctx=Load()), 
                              Name(id='reserve', ctx=Load()),
                              Constant(value=0)
                          ], 
                          keywords=[]))])])
"""