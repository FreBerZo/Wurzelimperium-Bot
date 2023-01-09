#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

from enum import Enum

from wurzelbot.HTTPCommunication import http_connection
from wurzelbot.Produktdaten import product_data, ProductType


class ShelfType(Enum):
    NORMAL = 'normal'
    DECORATION = 'decoration'
    WATER = 'water'
    HERB = 'herb'
    HONEY = 'honey'
    SNAIL = 'snail'

# TODO: check if this is correct
PRODUCTTYPE_TO_SHELFTYPE = {
    ShelfType.NORMAL: [ProductType.DECORATION, ProductType.VEGETABLES],
    ShelfType.DECORATION: [ProductType.ADORNMENTS],
    ShelfType.WATER: [ProductType.WATER_PLANTS, ProductType.WATER_DECORATION],
    ShelfType.HERB: [ProductType.HERBS],
    ShelfType.HONEY: [ProductType.HONEY],
    ShelfType.SNAIL: [ProductType.SNAIL],
}

class Box:
    def __init__(self, product, quantity):
        self.product = product
        self.quantity = quantity
        self.lru = time.time()

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
        return self.product.min_quantity()

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


class Shelf:
    slots_per_page = 20

    def __init__(self, shelf_type):
        self.shelf_type = shelf_type
        self.num_pages = None
        self.max_pages = None
        self.boxes = []
        self.product_ids = []

    def is_full(self):
        return len(self.boxes) >= self.slots_per_page * self.num_pages

    def get_boxes(self, product_type=None):
        if product_type is None:
            return self.boxes
        return [box for box in self.boxes if box.product.product_type == product_type]

    def get_products(self, product_type=None):
        return [box.product for box in self.get_boxes(product_type)]

    def get_box_for_product(self, product):
        for box in self.boxes:
            if box.product == product:
                return box
        return None

    def load_shelf(self, data=None):
        if data is None:
            data = http_connection.get_inventory(self.shelf_type.value)
            self.num_pages = int(data['regalzahl'])
            self.max_pages = int(data['maxRegale'])

        self.product_ids = data['sort'][self.shelf_type.value]
        inventory = data['produkte']
        inventory = {key: value for key, value in inventory.items() if key in self.product_ids}

        if len(self.boxes) == 0:
            for product_id, quantity in inventory.items():
                self.boxes.append(Box(product_data.get_product_by_id(product_id), quantity))
        else:
            new_boxes = []
            for product_id, quantity in inventory.items():
                product = product_data.get_product_by_id(product_id)
                box = self.get_box_for_product(product)
                if box is None:
                    box = Box(product, quantity)
                else:
                    box.quantity = quantity
                new_boxes.append(box)
            self.boxes = new_boxes


class Storage:
    
    def __init__(self):
        self.shelves = [
            Shelf(ShelfType.NORMAL),
            Shelf(ShelfType.DECORATION),
            Shelf(ShelfType.WATER),
            Shelf(ShelfType.HERB),
            Shelf(ShelfType.HONEY),
            Shelf(ShelfType.SNAIL),
        ]
        self.__storage = []

    def load_storage(self, efficient_load=True):
        """
        Führt ein Update des Lagerbestands für alle Produkte durch.
        """
        inventory = None
        for shelf in self.shelves:
            if efficient_load:
                if inventory is None:
                    inventory = http_connection.get_inventory(ShelfType.NORMAL.value)
                shelf.load_shelf(inventory)
            else:
                shelf.load_shelf()

    def get_shelf(self, shelf_type):
        for shelf in self.shelves:
            if shelf.shelf_type == shelf_type:
                return shelf
        raise AttributeError("Unknown shelf type: {}".format(shelf_type))

    def get_boxes(self, shelf_type=None, product_type=None):
        if shelf_type is None:
            return [box for shelf in self.shelves for box in shelf.get_boxes(product_type)]
        return self.get_shelf(shelf_type).get_boxes(product_type)

    def get_ordered_boxes(self, shelf_type=None, product_type=None):
        return [box for box in
                sorted(self.get_boxes(shelf_type, product_type), key=lambda box: box.quantity) if not box.is_empty()]

    def is_empty(self, shelf_type=None, product_type=None):
        for box in self.get_boxes(shelf_type, product_type):
            if not box.is_empty():
                return False
        return True

    def is_full(self, shelf_type):
        return self.get_shelf(shelf_type).is_full()

    def get_products(self, shelf_type=None, product_type=None):
        return [box.product for box in self.get_boxes(shelf_type, product_type)]

    def get_shelf_type_by_product(self, product):
        for shelf in self.shelves:
            if product in shelf.product_ids:
                return shelf.shelf_type
        return None

    def get_shelf_type_by_product_type(self, product_type):
        for shelf_type, product_types in PRODUCTTYPE_TO_SHELFTYPE.items():
            if product_type in product_types:
                return shelf_type
        return None

    def get_box_for_product(self, product):
        for box in self.get_boxes():
            if box.product == product:
                return box
        return None

    def get_stock_from_product(self, product):
        box = self.get_box_for_product(product)
        if box is None:
            return 0
        return box.quantity

    def get_potential_stock_from_product(self, product):
        from wurzelbot.gardener import gardener
        return gardener.get_potential_quantity_of(product)

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

    def get_lowest_box(self, shelf_type=None, product_type=None):
        if self.is_empty(shelf_type, product_type):
            return None
        return self.get_ordered_boxes(shelf_type, product_type)[0]

    def use_product(self, product):
        box = self.get_box_for_product(product)
        if box is None:
            return

        box.lru = time.time()

    def print(self):
        lines = []
        for box in self.get_boxes():
            lines.append('{}Amount: {}'.format(box.product.name.ljust(30), str(box.quantity).rjust(5)))

        if len(lines) > 0:
            print("\n".join(lines))
        else:
            print('Your stock is empty')


storage = Storage()
