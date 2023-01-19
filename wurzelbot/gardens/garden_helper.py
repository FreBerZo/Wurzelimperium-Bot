from wurzelbot.product.storage import Storage, Box, ShelfType, ProductType
from .gardens import GardenManager, PlantCrop


class GardenHelper:
    @staticmethod
    def get_potential_quantity_of(product):
        planted_quantity = 0
        for crop in GardenManager().get_crops_flat_from_class(PlantCrop):
            if crop.product == product:
                planted_quantity += 1
        return Storage().get_stock_from_product(product) + planted_quantity * product.harvest_quantity

    @staticmethod
    def get_potential_plants():
        """Returns all owned seeds ordered by the quantity in storage and potential seeds after harvesting"""
        boxes = []
        for box in Storage().get_boxes(ShelfType.NORMAL, ProductType.VEGETABLES):
            boxes.append(Box(box.product, box.quantity))
        for storage_box in boxes:
            for planted_box in GardenHelper.get_num_of_planted_plants():
                if storage_box.product == planted_box.product:
                    storage_box.quantity += planted_box.quantity * planted_box.product.harvest_quantity
        return [box.product for box in sorted(boxes)]

    @staticmethod
    def get_num_of_planted_plants():
        products = {}
        for crop in GardenManager().get_crops_flat_from_class(PlantCrop):
            if crop.product in products.keys():
                products[crop.product] += 1
            else:
                products[crop.product] = 1
        return [Box(product, quantity) for product, quantity in products.items()]
