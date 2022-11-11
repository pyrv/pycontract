
import os
from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Auction
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

    Like test 4 but with all conditions as part of the patterns, but now relying
    on ordered evaluation of case statements so we do not need to write negated
    patterns.
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
                case Bid(self.item, amount):
                    return error(f'bid {amount} for item {self.item} is not above {self.prev_bid}')
                case Sell(self.item) if self.prev_bid > self.reserve:
                    return ok
                case Sell(self.item):
                    return error(f'item {self.item} sold below reserve {self.reserve}')


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test6.Auction.test.pu', DIR + 'test6.Auction.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = Auction()
        set_debug(True)

        trace = [
            List('Hat', 50),
            List('Car', 5000),
            Bid('Hat', 30),
            Bid('Hat', 60),
            Bid('Car', 6000),
            Sell('Hat'),
            Sell('Car')
        ]
        m.verify(trace)

        errors_expected = []
        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)

    def test2(self):
        m = Auction()
        set_debug(True)

        trace = [
            List('Hat', 50),
            List('Car', 5000),
            Bid('Hat', 30),
            Bid('Hat', 20),
            Bid('Car', 4000),
            Sell('Hat'),
            Sell('Car')
        ]
        m.verify(trace)

        errors_expected = [
            "*** error transition in Auction:\n    state Listed('Hat', 50, 30)\n    event 4 Bid(item='Hat', amount=20)\n    bid 20 for item Hat is not above 30",
            "*** error transition in Auction:\n    state Listed('Car', 5000, 4000)\n    event 7 Sell(item='Car')\n    item Car sold below reserve 5000"]

        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)


