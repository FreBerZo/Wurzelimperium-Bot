import logging

from wurzelbot.account_data import AccountData
from wurzelbot.communication.http_communication import HTTPConnection
from wurzelbot.product.storage import Storage, Box, ShelfType, ProductType
from wurzelbot.trading.trader import Trader
from wurzelbot.utils.singelton_type import SingletonType
from .gardens import GardenManager, PlantCrop


class Gardener(metaclass=SingletonType):
    # TODO: remove this function from here
    def get_potential_quantity_of(self, product):
        planted_quantity = 0
        for crop in GardenManager().get_crops_flat_from_class(PlantCrop):
            if crop.product == product:
                planted_quantity += 1
        return Storage().get_stock_from_product(product) + planted_quantity * product.harvest_quantity

    # TODO: remove this function from here
    def get_potential_plants(self):
        """Returns all owned seeds ordered by the quantity in storage and potential seeds after harvesting"""
        boxes = []
        for box in Storage().get_boxes(ShelfType.NORMAL, ProductType.VEGETABLES):
            boxes.append(Box(box.product, box.quantity))
        for storage_box in boxes:
            for planted_box in GardenManager().get_num_of_planted_plants():
                if storage_box.product == planted_box.product:
                    storage_box.quantity += planted_box.quantity * planted_box.product.harvest_quantity
        return [box.product for box in sorted(boxes)]

    def get_num_of_planted_plants(self):
        products = {}
        for crop in GardenManager().get_crops_flat_from_class(PlantCrop):
            if crop.product in products.keys():
                products[crop.product] += 1
            else:
                products[crop.product] = 1
        return [Box(product, quantity) for product, quantity in products.items()]

    def plant(self, product, amount=-1):
        if not product.is_plant() or not product.is_plantable:
            return 0

        if amount == 0:
            return 0

        logging.info("planting {}...".format(product.name))

        product_stock = Storage().get_stock_from_product(product)
        if amount < 0 or amount > product_stock:
            amount = product_stock

        planted = 0

        empty_tiles = GardenManager().get_empty_tiles()
        updated_empty_tiles = set(empty_tiles)

        for tile in empty_tiles:
            if tile in updated_empty_tiles and tile.plant_fits(product.size):
                tiles = []
                for y in range(product.size[1]):
                    for x in range(product.size[0]):
                        tiles.append(tile.garden.garden_field.get_tile(tile.pos_x + x, tile.pos_y + y))
                tile_ids = [tile.tile_id for tile in tiles]
                HTTPConnection().grow_plant(tile.tile_id, product.id, tile.garden.garden_id, tile_ids)
                updated_empty_tiles.difference_update(set(tiles))
                planted += 1
                if planted >= amount > 0:
                    break

        logging.info("{} has been planted {} times".format(product.name, planted))

        Storage().load_storage()
        GardenManager().update_all()
        Storage().use_product(product)
        return planted

    def harvest(self):
        logging.info("harvesting...")
        harvested = False

        for garden in GardenManager().gardens:
            harvestable_products = garden.get_harvestable_products()
            if len(harvestable_products) > 0:
                Trader().make_space_in_storage_for_products(harvestable_products)
                garden.harvest()
                harvested = True

        if AccountData().aqua_garden_available:
            GardenManager().aqua_garden.harvest()
            harvested = True

        if harvested:
            HTTPConnection().cancel_all_contracts()
            Storage().load_storage()
            GardenManager().update_all()
        else:
            logging.info("nothing to harvest")

    def water(self):
        logging.info("watering...")
        watered = False

        for garden in GardenManager().gardens:
            if len(garden.get_tiles_to_be_watered()) > 0:
                garden.water_plants()
                watered = True

        if AccountData().aqua_garden_available:
            GardenManager().aqua_garden.water_plants()

        if watered:
            Storage().load_storage()
            GardenManager().update_all()
        else:
            logging.info("nothing to water")

    def remove_crop(self, crop):
        # it is assumed that a weed crop only occupies one tile
        tile = crop.tiles[0]

        logging.info("remove weed {} in garden {}".format(tile.tile_id, tile.garden.garden_id))

        HTTPConnection().remove_weed(tile.garden.garden_id, tile.tile_id)

        GardenManager().update_all()
        AccountData().load_user_data()
