#!/usr/bin/env python
# -*- coding: utf-8 -*-

from wurzelbot.HTTPCommunication import http_connection
from wurzelbot.Garten import garden_manager
from wurzelbot.Produktdaten import product_data
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

    def get_most_profitable_product(self):
        product_wins = []
        for product in product_data.get_tradable_plants():
            product_wins.append((product, self.relative_win_for(product)))

        return sorted(product_wins, key=lambda item: item[1], reverse=True)[0][0]

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


trader = Trader()
        