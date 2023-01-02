from wurzelbot.HTTPCommunication import http_connection
from wurzelbot.Lager import storage
from wurzelbot.Produktdaten import Category
from wurzelbot.Garten import garden_manager, PlantCrop
from wurzelbot.Spieler import spieler
import logging


class Gardener:
    def get_potential_quantity_of(self, product):
        planted_quantity = 0
        for crop in garden_manager.get_crops_flat_from_class(PlantCrop):
            if crop.product == product:
                planted_quantity += 1
        return storage.get_stock_from_product(product) + planted_quantity * product.harvest_quantity

    def get_potential_plants(self):
        """Returns all owned seeds ordered by the quantity in storage and potential seeds after harvesting"""
        boxes = list(storage.get_boxes_from_category(Category.VEGETABLES))
        for storage_box in boxes:
            for planted_box in garden_manager.get_num_of_planted_plants():
                if storage_box.product == planted_box.product:
                    storage_box.quantity += planted_box.quantity * planted_box.product.harvest_quantity
        return [box.product for box in sorted(boxes)]

    def plant(self, product, amount=-1):
        if not product.is_plant() or not product.is_plantable:
            return False

        product_stock = storage.get_stock_from_product(product)
        if amount < 0 or amount > product_stock:
            amount = product_stock

        planted = 0

        empty_tiles = garden_manager.get_empty_tiles()
        updated_empty_tiles = set(empty_tiles)

        for tile in empty_tiles:
            if tile in updated_empty_tiles and tile.plant_fits(product.size):
                tiles = []
                for y in range(product.size[1]):
                    for x in range(product.size[0]):
                        tiles.append(tile.garden.garden_field.get_tile(tile.pos_x + x, tile.pos_y + y))
                tile_ids = [tile.tile_id for tile in tiles]
                http_connection.grow_plant(tile.tile_id, product.id, tile.garden.garden_id, tile_ids)
                updated_empty_tiles.difference_update(set(tiles))
                planted += 1
                if planted >= amount > 0:
                    break

        logging.info("{} wurde {} mal gepflanzt.".format(product.name, planted))

        storage.update_storage()
        garden_manager.update_all()
        return True

    def harvest(self):
        logging.info("Alle Pflanzen werden geerntet")
        for garden in garden_manager.gardens:
            garden.harvest()

        if spieler.is_aqua_garden_available():
            garden_manager.aqua_garden.harvest()

        storage.update_storage()
        garden_manager.update_all()

    def water(self):
        logging.info("Alle Pflanzen werden gegossen.")
        for garden in garden_manager.gardens:
            garden.water_plants()

        if spieler.is_aqua_garden_available():
            garden_manager.aqua_garden.water_plants()

        storage.update_storage()
        garden_manager.update_all()


gardener = Gardener()
