import datetime
import time

from wurzelbot.communication.http_communication import HTTPConnection
from wurzelbot.gardens.gardens import GardenManager
from wurzelbot.product.product_data import ProductData
from wurzelbot.account_data import AccountData
from wurzelbot.utils.singelton_type import SingletonType


class Market(metaclass=SingletonType):
    """Data collection for every place where trading is done"""
    PRICE_CACHE_TIME = datetime.timedelta(minutes=10).total_seconds()

    def __init__(self):
        self.wimp_data = {}
        # lazy loaded prices; need reloading after one day
        # {product: (sell_price, up-to-date_until) }
        self._product_prices = {}
        self._products_ordered_by_profitability = None

    def load_wimp_data(self):
        for garden in GardenManager().gardens:
            self.wimp_data.update({garden.garden_id: HTTPConnection().get_wimps_data(garden.garden_id)})

    def dispose_profitability(self):
        self._products_ordered_by_profitability = None

    def get_products_ordered_by_profitability(self):
        if self._products_ordered_by_profitability is not None:
            return self._products_ordered_by_profitability
        product_wins = []
        for product in ProductData().get_tradable_plants():
            product_wins.append((product, self.relative_win_for(product)))

        return [item[0] for item in sorted(product_wins, key=lambda item: item[1], reverse=True)]

    def min_money(self):
        return GardenManager().get_num_of_plantable_tiles() * self.get_sell_price_for(
            self.get_most_profitable_product())

    def min_sell_quantity(self, product):
        return GardenManager().get_num_of_plantable_tiles() * (product.harvest_quantity - 1) \
            * datetime.timedelta(days=1).total_seconds() \
            / (product.time_until_harvest * product.size[0] * product.size[1])

    def get_most_profitable_product(self):
        return self.get_products_ordered_by_profitability()[0]

    def relative_win_for(self, product):
        if not product.is_tradable:
            return None
        return (self.get_win_for(product) * datetime.timedelta(days=1).total_seconds() * (product.harvest_quantity - 1)) \
            / (product.time_until_harvest * product.size[0] * product.size[1])

    def get_win_for(self, product):
        return self.get_sell_price_for(product) * 0.9

    def get_sell_price_for(self, product):
        if not product.is_tradable:
            raise AttributeError(f'product {product}({product.id}) is not tradeable and doesn\'t have a sell price')

        data = self._product_prices.get(product)
        if data is not None and time.time() < data[1]:
            return data[0]

        market_price = self.get_cheapest_offer(product)
        official_price = product.price_npc
        sell_price = min(market_price, official_price) - 0.01
        self._product_prices.update({product: (sell_price, time.time() + self.PRICE_CACHE_TIME)})
        return sell_price

    def get_cheapest_offer(self, product):
        offers = self.get_offers_for(product)

        if len(offers) > 0:
            return offers[0][1]
        return None

    def get_offers_for(self, product, exclude_own=True):
        if not product.is_tradable:
            raise AttributeError(f'product {product}({product.id}) is not tradeable and doesn\'t have offers')

        result = HTTPConnection().get_offers_from_product(product.id)
        if exclude_own:
            return [item for item in result if item[2] != AccountData.user_name]
        return result
