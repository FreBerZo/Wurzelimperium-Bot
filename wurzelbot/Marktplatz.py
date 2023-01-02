#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from wurzelbot.HTTPCommunication import http_connection
from wurzelbot.Garten import garden_manager
from wurzelbot.gardener import gardener
from wurzelbot.Produktdaten import product_data
from wurzelbot.Spieler import spieler
from wurzelbot.Lager import storage
from wurzelbot.utils import cache
import datetime

'''
Created on 15.05.2019

@author: MrFlamez
'''


class Trader:
    
    def __init__(self):
        # TODO: this shouldn't be cached here maybe make some wimp class
        self.wimp_data = {}

    def load_wimp_data(self):
        for garden in garden_manager.gardens:
            self.wimp_data.update({garden.garden_id: http_connection.get_wimps_data(garden.garden_id)})

    def reject_bad_wimp_offers(self):
        for garden_id, offers in self.wimp_data.items():
            for wimp_id, data in offers.items():
                offered_money = data[0]
                requested_products = data[1]
                worth = 0
                for product_id, quantity in requested_products.items():
                    worth += self.get_win_for(product_data.get_product_by_id(product_id)) * quantity

                # wimps seem to never offer the actual worth, but they give point for selling so 80% of the actual worth
                # is enough for selling
                if worth * 0.8 > offered_money:
                    http_connection.decline_wimp(wimp_id)

    @cache(86400)
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
            # TODO: this should be cached somehow maybe with some market class
            # TODO: somehow exclude own offers
            return http_connection.get_offers_from_product(product.id)
        return []
    
    def findBigGapInProductOffers(self, id, npcPrice):
        """
        Ermittelt eine große Lücke (> 10 %) zwischen den Angeboten und gibt diese zurück.
        """
        
        listOffers = self.get_offers_for(id)
        listPrices = []

        if (listOffers != None):
            
            #Alle Preise in einer Liste sammeln
            for element in listOffers:
                listPrices.append(element[1])
            
            if (npcPrice != None and id != 0): #id != 0: Coins nicht sortieren
                iList = range(0, len(listPrices))
                iList.reverse()
                for i in iList:
                    if listPrices[i] > npcPrice:
                        del listPrices[i]
            
            gaps = []
            #Zum Vergleich werden mindestens zwei Einträge benötigt.
            if (len(listPrices) >= 2):
                for i in range(0, len(listPrices)-1):
                    if (((listPrices[i+1] / 1.1) - listPrices[i]) > 0.0):
                        gaps.append([listPrices[i], listPrices[i+1]])
            
            return gaps

    def buy_cheapest_of(self, product, quantity, money=None):
        # TODO: what if shelf is full?
        if money is None:
            money = spieler.money - self.min_money
        if money <= 0:
            return
        offers = http_connection.get_cheapest_offers_for(product)
        rest_quantity = quantity
        for offer in offers:
            if product.buy_in_shop is not None and offer.get('price') > product.price_npc:
                buy_quantity = rest_quantity
                if money < product.price_npc * buy_quantity:
                    buy_quantity = int(money/product.price_npc)
                if buy_quantity > 0:
                    http_connection.buy_from_shop(product.buy_in_shop.value, product.id, buy_quantity)
                    money -= product.price_npc * buy_quantity
                    rest_quantity -= buy_quantity
                break

            offer_amount = offer.get('amount')
            offer_price = offer.get('price')
            buy_quantity = rest_quantity
            if offer_amount < rest_quantity:
                buy_quantity = offer_amount
            if money < buy_quantity * offer_price:
                buy_quantity = int(money/offer_price)

            if buy_quantity > 0:
                http_connection.buy_from_marketplace(product, offer, buy_quantity)
                money -= offer_price * buy_quantity
                rest_quantity -= buy_quantity

            if rest_quantity <= 0 or money < offer_price:
                break

        if rest_quantity > 0:
            # TODO: what to do in this case?
            pass

        logging.info('bought {} {}s'.format(quantity - rest_quantity, product))

        spieler.load_user_data()

    def sell_to_marketplace(self, product, quantity, price):
        http_connection.sell_to_marketplace(product, quantity, price)
        spieler.load_user_data()

    def sell_max_of(self, product):
        real_stock = storage.get_stock_from_product(product)
        if real_stock == 0:
            return

        potential_stock = gardener.get_potential_quantity_of(product)
        min_quantity = storage.get_box_for_product(product).min_quantity()
        sell_amount = potential_stock - min_quantity
        if sell_amount <= 0:
            return
        if sell_amount > real_stock:
            sell_amount = real_stock

        money_problem = False
        sell_price = self.get_sell_price_for(product)
        if sell_price * sell_amount * 0.1 > spieler.money:
            sell_amount = int(spieler.money / (sell_price * 0.1))
            money_problem = True
        if sell_amount > self.min_sell_quantity() or money_problem:
            self.sell_to_marketplace(product, sell_amount, self.get_sell_price_for(product))


trader = Trader()
        