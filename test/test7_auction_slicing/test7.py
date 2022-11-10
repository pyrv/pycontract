
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

    Like test 4 but with all conditions as part of the patterns, and using slicing to
    avoid negative patterns. Slicing becomes active when the key function is overridden.
    """

    def key(self, event: Event) -> str:
        match event:
            case List(item, _):
                return item
            case Bid(item, _):
                return item
            case Sell(item):
                return item

    @initial
    class Always(State):
        def transition(self, event):
            match event:
                case List(item, reserve):
                    return self.Listed(item, reserve, 0)

    @data
    class Listed(NextState):
        item: str
        reserve: int
        prev_bid: int

        def transition(self, event):
            match event:
                case Bid(self.item, amount) if amount > self.prev_bid:
                    return self.Listed(self.item, self.reserve, amount)
                case Sell(self.item) if self.prev_bid > self.reserve:
                    return ok


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test7.Auction.test.pu', DIR + 'test7.Auction.pu')


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
        errors_actual = m.get_all_messages()
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
            "*** error transition in Auction:\n    state Listed('Hat', 50, 30)\n    event 4 Bid(item='Hat', amount=20)\n    no transition matching event",
            "*** error transition in Auction:\n    state Listed('Car', 5000, 4000)\n    event 7 Sell(item='Car')\n    no transition matching event"]

        errors_actual = m.get_all_messages()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)


