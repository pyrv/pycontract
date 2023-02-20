
from pycontract import *
import unittest
import test.utest
import inspect

"""
Auction. This is test 5 - but here experimenting with extracting 
information from the code using inspect.  This comes down to
a string processing problem using Pythons string functions,
including possibly regular expressions. The inspect module gives us
the source code of the patterns, either in one chunk 
or line by line per function. Then we have to do the rest.
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


def is_state_class(member: object) -> bool:
    return inspect.isclass(member) and issubclass(member, State)


def is_transition_function(member: object) -> bool:
    return inspect.isfunction(member) and member.__name__ == 'transition'


class Test1(unittest.TestCase):
    def test1(self):
        m = Auction()
        for (state_name, state) in inspect.getmembers(m, predicate=is_state_class):
            print(f'{state_name}:')
            for (fun_name, function) in inspect.getmembers(state, predicate=is_transition_function):
                for line in inspect.getsourcelines(function):
                    if isinstance(line, list):
                        for stmt in line:
                            stmt_stripped = stmt.strip()
                            if stmt_stripped.startswith('case'):
                                stmt_no_case = stmt_stripped.lstrip('case')
                                split = stmt_no_case.split('if')
                                print(f'  {split}')

        """
        This will print:
        
        Always:
          [' List(item, reserve):']
        Listed:
          [' Bid(self.item, amount) ', ' amount > self.prev_bid:']
          [' Bid(self.item, amount) ', ' amount <= self.prev_bid:']
          [' Sell(self.item) ', ' self.prev_bid > self.reserve:']
          [' Sell(self.item) ', ' self.prev_bid <= self.reserve:']
        
        These can then further be processed with string processing
        functions. It becomes a string processing problem.
        """


