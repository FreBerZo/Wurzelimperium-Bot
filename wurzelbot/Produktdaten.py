#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 23.05.2019

@author: MrFlamez
'''
 
import json
from wurzelbot.HTTPCommunication import http_connection
from wurzelbot.trading import Shop
from enum import Enum


class ProductType(Enum):
    DECORATION = 'd'
    HERBS = 'h'
    HONEY = 'honey'
    WATER_PLANTS = 'w'
    VEGETABLES = 'v'
    WATER_DECORATION = 'wd'
    COINS = 'c'
    ADORNMENTS = 'z'
    SNAIL = 'snail'
    OTHER = 'u'


class Product:
    def __init__(self, id, product_type, sx, sy, name, lvl, crop, plantable, time):
        self.id = id
        if product_type == '':
            product_type = 'c'
        self.product_type = ProductType(product_type)
        self.size = (sx, sy)
        self.name = name.decode('UTF-8')
        self.level = lvl
        self.harvest_quantity = crop
        self.is_plantable = plantable
        self.time_until_harvest = time
        self.price_npc = None
        # note that not yet unlocked plants are not tradable
        self.is_tradable = False
        self.buy_in_shop = None

    def __str__(self):
        return self.name

    def is_plant(self):
        return self.product_type == ProductType.VEGETABLES

    def is_decoration(self):
        return self.product_type == ProductType.DECORATION

    def min_quantity(self):
        if self.is_plant():
            from wurzelbot.Garten import garden_manager
            return int(garden_manager.get_num_of_plantable_tiles() / (self.size[0] * self.size[1]))
        return 0

    def print_all(self):
        # Show nothing instead of None
        xstr = lambda s: s or ""

        print('ID:', str(self.id).rjust(3), ' ',
              'CAT:', str(self.product_type.name).ljust(5), ' ',
              'Name:', str(self.name).ljust(35), ' ',
              'Plantable:', str(self.is_plantable).ljust(5), ' ',
              'NPC:', str(xstr(self.price_npc)).rjust(6), ' ',
              'Size:', str(xstr(self.size)), ' ')


class ProductData:
    
    def __init__(self):
        self.__products = []
    
    def load_prices(self):
        """
        Ermittelt alle möglichen NPC Preise und setzt diese in den Produkten.
        """
        npc_prices = http_connection.get_npc_prices()
        for product in self.__products:
            if product.name in npc_prices.keys():
                product.price_npc = npc_prices[product.name]
                
        # Coin manuell setzen, dieser ist in der Tabelle der Hilfe nicht enthalten
        coins = self.get_product_by_name('Coins')
        coins.price_npc = float(300)

    def load_tradable_products(self):
        for product_id in http_connection.get_all_tradeable_products_from_overview():
            self.get_product_by_id(product_id).is_tradable = True

    def load_shops(self):
        # TODO: add flower shop, but it's more complicated because it's only open at wed and sat
        shops = [Shop.TREE, Shop.FARM, Shop.DECORATION]

        for shop in shops:
            product_ids = http_connection.get_product_ids_from_shop(shop.value)
            for product_id in product_ids:
                self.get_product_by_id(product_id).buy_in_shop = shop
    
    def get_product_by_id(self, product_id):
        for product in self.__products:
            if int(product_id) == product.id:
                return product

    def get_product_by_crop_id(self, crop_id):
        for product in self.__products:
            if int(crop_id) == product.crop_id:
                return product
            
    def get_product_by_name(self, name):
        for product in self.__products:
            if name.lower() == product.name.lower():
                return product
        return None

    def get_tradable_plants(self):
        return [product for product in self.__products if product.is_tradable and product.is_plant()]
        
    def get_list_of_all_product_ids(self):
        return [product.id for product in self.__products]

    def init_products(self):
        """
        Initialisiert alle Produkte.
        """
        products = dict(json.loads(http_connection.get_all_product_informations()))
        # Nicht genutzte Attribute: img, imgPhase, fileext, clear, edge, pieces, speedup_cooldown in Kategorie z
        for key in sorted(products.keys()):
            # 999 ist nur ein Testeintrag und wird nicht benötigt.
            if key == '999':
                continue

            name = products[key]['name'].replace('&nbsp;', ' ')
            self.__products.append(Product(id=int(key),
                                           product_type=products[key]['category'],
                                           sx=products[key]['sx'],
                                           sy=products[key]['sy'],
                                           name=name.encode('utf-8'),
                                           lvl=products[key]['level'],
                                           crop=products[key]['crop'],
                                           plantable=products[key]['plantable'],
                                           time=products[key]['time']))
                
        self.load_prices()
        self.load_tradable_products()
        self.load_shops()
    
    def print_all(self):
        for product in sorted(self.__products, key=lambda x: x.name.lower()):
            product.print_all()

    def print_all_plants(self):
        for product in sorted(self.__products, key=lambda x: x.name.lower()):
            if not product.is_plant():
                continue

            product.print_all()


product_data = ProductData()
