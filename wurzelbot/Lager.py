#!/usr/bin/env python
# -*- coding: utf-8 -*-

from wurzelbot.HTTPCommunication import http_connection
from wurzelbot.Produktdaten import product_data


class Box:
    def __init__(self, product, quantity):
        self.product = product
        self.quantity = quantity

    def __str__(self):
        return "{}: {}".format(self.product.name, self.quantity)

    def __lt__(self, other):
        return self.quantity < other.quantity

    def is_empty(self):
        return self.quantity <= 0

    def potential_quantity(self):
        from wurzelbot.gardener import gardener
        return gardener.get_potential_quantity_of(self.product)

    def min_quantity(self):
        from Garten import garden_manager
        return int(garden_manager.get_num_of_plantable_tiles() / (self.product.size[0] * self.product.size[1]))

    def is_min_quantity(self):
        return self.min_quantity() <= self.quantity

    def is_potential_min_quantity(self):
        return self.potential_quantity() >= self.min_quantity()

    @staticmethod
    def merge_boxes(boxes1, boxes2):
        merged_boxes = {}

        # Add all boxes from the first set to the dictionary
        for box in boxes1:
            merged_boxes[box.product] = box.quantity

        # Add all boxes from the second set to the dictionary,
        # updating the quantity if the product already exists
        for box in boxes2:
            if box.product in merged_boxes:
                merged_boxes[box.product] += box.quantity
            else:
                merged_boxes[box.product] = box.quantity

        # Convert the dictionary back into a list of Box objects
        merged_boxes_list = [Box(product, quantity) for product, quantity in merged_boxes.items()]
        return merged_boxes_list


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

    def get_boxes_from_category(self, cat):
        return [box for box in self.__storage if box.product.category == cat]

    def get_ordered_products_from_category(self, cat):
        return [box.product for box in sorted(self.__storage) if box.product.category == cat]

    def get_box_for_product(self, product):
        for box in self.__storage:
            if box.product == product:
                return box
        return None

    def get_stock_from_product(self, product):
        box = self.get_box_for_product(product)
        if box is None:
            return 0
        return box.quantity

    def get_ordered_storage(self):
        return [box for box in sorted(self.__storage, key=lambda box: box.quantity) if not box.is_empty()]

    def has_potential_min_quantity_for(self, product):
        box = self.get_box_for_product(product)
        if box is None:
            return False
        return self.get_box_for_product(product).is_potential_min_quantity()

    def has_min_quantity_for(self, product):
        box = self.get_box_for_product(product)
        if box is None:
            return False
        return self.get_box_for_product(product).is_min_quantity()

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
