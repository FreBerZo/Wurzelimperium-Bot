"""
Created on 15.05.2019

@author: MrFlamez
"""

import logging

from wurzelbot.account_data import account_data
from wurzelbot.communication.http_communication import http_connection
from wurzelbot.product.product_data import product_data
from wurzelbot.product.storage import storage
from .market import market


class Trader:

    def reject_bad_wimp_offers(self):
        declined_wimps = 0
        for garden_id, offers in market.wimp_data.items():
            for wimp_id, data in offers.items():
                offered_money = data[0]
                requested_products = data[1]
                worth = 0
                for product_id, quantity in requested_products.items():
                    worth += market.get_win_for(product_data.get_product_by_id(product_id)) * quantity

                # wimps seem to never offer the actual worth, but they give point for selling so 80% of the actual worth
                # is enough for selling
                if worth * 0.8 > offered_money:
                    declined_wimps += 1
                    http_connection.decline_wimp(wimp_id)
        logging.info(f"declined {declined_wimps} wimp(s)")

    def make_space_in_storage_for_products(self, products):
        """
        Makes a contract to temporarily move products out of the storage so all products stated in the products
        attribute can be added to the storage. Don't forget to cancel all contracts after adding the desired products.
        """
        if len(products) == 0:
            return
        product_type = products[0].product_type
        shelf_type = storage.get_shelf_type_by_product_type(product_type)
        shelf = storage.get_shelf(shelf_type)

        # This works because it is possible to overfill the storage by creating and cancelling contracts.
        # Normally players can't plant plants that can not be shown in storage, if overfilled because of a
        # UI problem, but the bot doesn't care. Therefor overfilling the storage is not a problem.
        products_in_shelf = storage.get_products(shelf_type)
        if len(list(set(products) - set(products_in_shelf))) == 0:
            return
        tradable_products_in_shelf = [product for product in storage.get_products(shelf_type, product_type)
                                      if product.is_tradable]
        removable_products = list(set(tradable_products_in_shelf) - set(products))
        max_space = shelf.num_pages * shelf.slots_per_page
        products_to_be_in_shelf = list(products_in_shelf)
        products_to_be_in_shelf.extend(products)
        num_of_products_to_be_in_shelf = len(list(set(products_to_be_in_shelf)))
        num_of_products_to_be_removed = num_of_products_to_be_in_shelf - max_space
        if num_of_products_to_be_removed <= 0:
            return
        if num_of_products_to_be_removed > len(removable_products):
            raise RuntimeError('Too many not tradable products are in the storage.')
        selected_products = removable_products[:num_of_products_to_be_removed]

        trade_products = {}
        for product in selected_products:
            price = product.price_npc
            if price is None:
                price = market.get_sell_price_for(product)
            trade_products[product] = {'quantity': storage.get_stock_from_product(product), 'price': price}
        logging.debug("handling overfilled storage by moving {} products to a temporary contract"
                      .format(len(trade_products)))
        http_connection.create_contract(account_data.user_name, trade_products)

    def buy_cheapest_of(self, product, quantity, money=None):
        if money is None:
            money = account_data.money - market.min_money()
        if money <= 0:
            return 0

        self.make_space_in_storage_for_products([product])

        buying_protocol = {}
        offers = http_connection.get_cheapest_offers_for(product)
        rest_quantity = quantity
        for offer in offers:
            if product.buy_in_shop is not None and offer.get('price') > product.price_npc:
                buy_quantity = rest_quantity
                if money < product.price_npc * buy_quantity:
                    buy_quantity = int(money / product.price_npc)
                if buy_quantity > 0:
                    http_connection.buy_from_shop(product.buy_in_shop.value, product.id, buy_quantity)
                    money -= product.price_npc * buy_quantity
                    rest_quantity -= buy_quantity
                    if buying_protocol.get(offer.get('price')) is None:
                        buying_protocol[offer.get('price')] = buy_quantity
                    else:
                        buying_protocol[offer.get('price')] += buy_quantity
                break

            offer_amount = offer.get('amount')
            offer_price = offer.get('price')
            buy_quantity = rest_quantity
            if offer_amount < rest_quantity:
                buy_quantity = offer_amount
            if money < buy_quantity * offer_price:
                buy_quantity = int(money / offer_price)

            if buy_quantity > 0:
                http_connection.buy_from_marketplace(product, offer, buy_quantity)
                money -= offer_price * buy_quantity
                rest_quantity -= buy_quantity

            if rest_quantity <= 0 or money < offer_price:
                break

        bought_quantity = quantity - rest_quantity

        http_connection.cancel_all_contracts()

        price_details = " | ".join("{} * {}".format(quantity, price) for price, quantity in buying_protocol.items())
        logging.info('bought {} {} times\n {}'.format(product, bought_quantity, price_details))

        account_data.load_user_data()
        storage.load_storage()
        storage.use_product(product)

        return bought_quantity

    def sell_to_marketplace(self, product, quantity, price):
        price = round(price, 2)
        http_connection.sell_to_marketplace(product, quantity, price)

        logging.info("sold {} {} for {}".format(quantity, product, price))

        account_data.load_user_data()
        storage.load_storage()
        storage.use_product(product)

    def sell(self, product, sell_amount=-1):
        real_stock = storage.get_stock_from_product(product)
        if real_stock == 0:
            return

        potential_stock = storage.get_potential_stock_from_product(product)
        min_quantity = storage.get_box_for_product(product).min_quantity()
        potential_sell_amount = potential_stock - min_quantity
        if sell_amount == -1 or sell_amount > potential_sell_amount:
            sell_amount = potential_sell_amount
        if sell_amount == 0:
            return
        if sell_amount > real_stock:
            sell_amount = real_stock

        money_problem = False
        sell_price = market.get_sell_price_for(product)
        if sell_price * sell_amount * 0.1 > account_data.money:
            sell_amount = int(account_data.money / (sell_price * 0.1))
            money_problem = True
        if sell_amount > market.min_sell_quantity() or money_problem:
            self.sell_to_marketplace(product, sell_amount, sell_price)


trader = Trader()
