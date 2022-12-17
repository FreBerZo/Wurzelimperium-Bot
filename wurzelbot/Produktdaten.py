#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 23.05.2019

@author: MrFlamez
'''
 
import json
from wurzelbot.HTTPCommunication import http_connection
from enum import Enum


class Category(Enum):
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
    def __init__(self, id, cat, sx, sy, name, lvl, crop_id, plantable, time):
        self.id = id
        if cat == '':
            cat = 'c'
        self.category = Category(cat)
        self.size = (sx, sy)
        self.name = name.decode('UTF-8')
        self.level = lvl
        self.crop_id = crop_id
        self.is_plantable = plantable
        self.time_until_harvest = time
        self.price_npc = None

    def is_plant(self):
        return self.category == Category.VEGETABLES

    def is_decoration(self):
        return self.category == Category.DECORATION

    def print_all(self):
        # Show nothing instead of None
        xstr = lambda s: s or ""

        print('ID:', str(self.id).rjust(3), ' ',
              'CAT:', str(self.category.name).ljust(5), ' ',
              'Name:', str(self.name).ljust(35), ' ',
              'Plantable:', str(self.is_plantable).ljust(5), ' ',
              'NPC:', str(xstr(self.price_npc)).rjust(6), ' ',
              'Size:', str(xstr(self.size)), ' ')


class ProductData:
    
    def __init__(self):
        self.__products = []
    
    def set_all_prices(self):
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
                                           cat=products[key]['category'],
                                           sx=products[key]['sx'],
                                           sy=products[key]['sy'],
                                           name=name.encode('utf-8'),
                                           lvl=products[key]['level'],
                                           crop_id=products[key]['crop'],
                                           plantable=products[key]['plantable'],
                                           time=products[key]['time']))
                
        self.set_all_prices()
    
    def print_all(self):
        for product in sorted(self.__products, key=lambda x: x.name.lower()):
            product.print_all()

    def print_all_plants(self):
        for product in sorted(self.__products, key=lambda x: x.name.lower()):
            if not product.is_plant():
                continue

            product.print_all()


product_data = ProductData()
