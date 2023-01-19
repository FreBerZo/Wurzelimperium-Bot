import datetime

from wurzelbot.communication.http_communication import http_connection
from wurzelbot.gardens.gardens import garden_manager
from wurzelbot.product.product_data import product_data
from wurzelbot.utils import cache


class Market:
    """Data collection for every place where trading is done"""

    def __init__(self):
        self.wimp_data = {}

    def load_wimp_data(self):
        for garden in garden_manager.gardens:
            self.wimp_data.update({garden.garden_id: http_connection.get_wimps_data(garden.garden_id)})

    # @cache(86400)
    def get_products_ordered_by_profitability(self):
        product_wins = []
        for product in product_data.get_tradable_plants():
            product_wins.append((product, self.relative_win_for(product)))

        return [item[0] for item in sorted(product_wins, key=lambda item: item[1], reverse=True)]

    @cache(86400)
    def min_money(self):
        return garden_manager.get_num_of_plantable_tiles() * self.get_sell_price_for(self.get_most_profitable_product())

    @cache(86400)
    def min_sell_quantity(self):
        # TODO: how about min sell quantity per product: amount is how much can be farmed in one day
        return garden_manager.get_num_of_plantable_tiles() * (self.get_most_profitable_product().harvest_quantity - 1)

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
            return None
        market_price = self.get_cheapest_offer(product)
        official_price = product.price_npc
        if market_price < official_price:
            return market_price - 0.01
        return official_price - 0.01

    def get_cheapest_offer(self, product):
        """
        Ermittelt das günstigste Angebot eines Produkts.
        """
        offers = self.get_offers_for(product)

        if len(offers) > 0:
            return offers[0][1]
        return None

    def get_offers_for(self, product):
        """
        Ermittelt alle Angebote eines Produkts.
        """

        if product.is_tradable:
            # TODO: this should be cached
            # TODO: somehow exclude own offers
            return http_connection.get_offers_from_product(product.id)
        return []


market = Market()
