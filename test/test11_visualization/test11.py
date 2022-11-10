
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
    """

    @initial
    class Always(AlwaysState):
        def transition(self, event):
            match event:
                case List(item, reserve) if reserve >= 0:
                    return self.Listed(item, reserve, 0)

    @data
    class Listed(State):
        item: str
        reserve: int
        prev_bid: int

        def transition(self, event):
            match event:
                case Bid(self.item, amount):
                    if amount > self.prev_bid:
                        return self.Listed(self.item, self.reserve, amount)
                    else:
                        return error(f'bid {amount} for item {self.item} is not above {self.prev_bid}')
                case Sell(self.item):
                    if self.prev_bid > self.reserve:
                        return ok
                    else:
                        return error(f'item {self.item} sold below reserve {self.reserve}')


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test11.Auction.test.pu', DIR + 'test11.Auction.pu')


