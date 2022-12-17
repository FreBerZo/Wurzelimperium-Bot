#!/usr/bin/env python
# -*- coding: utf-8 -*-

from wurzelbot.HTTPCommunication import http_connection
from wurzelbot.Produktdaten import product_data


class Box:
    def __init__(self, product, quantity):
        self.product = product
        self.quantity = quantity

    def __lt__(self, other):
        return self.quantity < other.quantity

    def is_empty(self):
        return self.quantity <= 0


class Storage:
    
    def __init__(self):
        self.__storage = []

    def update_storage(self):
        """
        Führt ein Update des Lagerbestands für alle Produkte durch.
        """
        self.__storage = []
        inventory = http_connection.get_inventory()
        
        for i in inventory:
            self.__storage.append(Box(product_data.get_product_by_id(i), inventory[i]))

    def is_empty(self):
        for box in self.__storage:
            if not box.is_empty():
                return False
        return True

    def get_products(self):
        return [box.product for box in self.__storage]

    def get_products_from_category(self, cat):
        return [box.product for box in self.__storage if box.product.category == cat]

    def get_ordered_products_from_category(self, cat):
        return [box.product for box in sorted(self.__storage) if box.product.category == cat]

    def get_box_for_product(self, product):
        for box in self.__storage:
            if box.product == product:
                return box

    def get_stock_from_product(self, product):
        return self.get_box_for_product(product).quantity

    def get_ordered_storage(self):
        return [box for box in sorted(self.__storage, key=lambda box: box.quantity) if not box.is_empty()]

    def get_lowest_box(self):
        if self.is_empty():
            return None
        return self.get_ordered_storage()[0]

    def print(self):
        lines = []
        for box in self.__storage:
            lines.append('{}Amount: {}'.format(box.product.name.ljust(30), str(box.quantity).rjust(5)))

        if len(lines) > 0:
            print("\n".join(lines))
        else:
            print('Your stock is empty')


storage = Storage()
