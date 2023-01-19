import logging

from wurzelbot.account_data import AccountData
from wurzelbot.communication.http_communication import HTTPConnection
from wurzelbot.product.storage import Storage
from wurzelbot.trading.trader import Trader
from .gardens import GardenManager


class Gardener:
    @staticmethod
    def plant(product, amount=-1):
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

    @staticmethod
    def harvest():
        logging.info("harvesting...")
        harvested = False

        for garden in GardenManager().gardens:
            harvestable_products = garden.get_harvestable_products()
            if len(harvestable_products) > 0:
                Trader.make_space_in_storage_for_products(harvestable_products)
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

    @staticmethod
    def water():
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

    @staticmethod
    def remove_crop(crop):
        # it is assumed that a weed crop only occupies one tile
        tile = crop.tiles[0]

        logging.info("remove weed {} in garden {}".format(tile.tile_id, tile.garden.garden_id))

        HTTPConnection().remove_weed(tile.garden.garden_id, tile.tile_id)

        GardenManager().update_all()
        AccountData().load_user_data()
