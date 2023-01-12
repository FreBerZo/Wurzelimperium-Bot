import datetime
import logging
import time

from wurzelbot.account_data import account_data
from wurzelbot.communication.http_communication import http_connection
from wurzelbot.product.product_data import product_data
# TODO: remove this import
from wurzelbot.product.storage import Box

GARDEN_WIDTH = 17
GARDEN_HEIGHT = 12


class Crop:
    pass


class PlantCrop(Crop):
    def __init__(self, product, harvest_time, watered_time, size, planted_time, tiles):
        self.product = product
        self.tiles = tiles
        self.harvest_time = harvest_time
        self.watered_time = watered_time
        self.size = size
        self.planted_time = planted_time

    def is_watered(self):
        # watering a plant holds for one day
        return self.next_water_time() > int(time.time())

    def get_first_tile(self):
        return self.tiles[0]

    def next_water_time(self):
        # watering a plant holds for one day
        return self.watered_time + datetime.timedelta(days=1).total_seconds()


class DecorationCrop(Crop):
    def __init__(self, product, size, tiles):
        self.product = product
        self.size = size
        self.tiles = tiles


class WeedCrop(Crop):
    def __init__(self, crop_id, remove_cost, size, tiles):
        self.crop_id = crop_id
        self.tiles = tiles  # fill this
        self.remove_cost = remove_cost
        self.size = size


class Tile:
    def __init__(self, x, y, tile_id, garden):
        self.pos_x = x
        self.pos_y = y
        self.tile_id = tile_id
        self.garden = garden
        self.crop = None

    def set_crop(self, crop):
        self.crop = crop

    def is_empty(self):
        return self.crop is None

    def plant_fits(self, size):
        return self.garden.plant_fits_at(size, self.pos_x, self.pos_y) and self.is_empty()

    def update(self, tile_data):
        width, height = str(tile_data[9]).split('x')[:2]
        size = (int(width), int(height))

        # a crop that spans multiple tiles will only be updated at the last tile of the crop
        x_pos = int(tile_data[1])
        y_pos = int(tile_data[2])
        if (size[0], size[1]) != (x_pos, y_pos):
            return

        if size[0] > 1 or size[1] > 1:
            # crop is bigger than 1x1
            tile_list = []
            for y in range(size[1], 0, -1):
                for x in range(size[0], 0, -1):
                    tile_list.append(self.garden.garden_field.get_tile(self.pos_x + 1 - x, self.pos_y + 1 - y))
        else:
            # crop is 1x1
            tile_list = [self]

        crop_id = int(tile_data[0])
        if crop_id == 0:
            # tile is empty
            crop = None
        elif crop_id in [41, 42, 43, 45]:
            # weed on tile
            crop = WeedCrop(crop_id, float(tile_data[6]), size, tile_list)
        else:
            # product on tile
            product = product_data.get_product_by_id(crop_id)
            if product.is_plant():
                # plant on tile
                crop = PlantCrop(product, int(tile_data[3]), int(tile_data[4]), size, int(tile_data[10]), tile_list)
            elif product.is_decoration():
                # decoration on tile
                crop = DecorationCrop(product, size, tile_list)
            else:
                crop = None

        for tile in tile_list:
            tile.set_crop(crop)


class Field:
    def __init__(self, garden):
        self.garden_field = []
        self.garden = garden

        i = 1
        for y in range(GARDEN_HEIGHT):
            self.garden_field.append([])
            for x in range(GARDEN_WIDTH):
                self.garden_field[y].append(Tile(x, y, i, garden))
                i += 1

    def get_tiles_flat(self):
        return [tile for row in self.garden_field for tile in row]

    @staticmethod
    def id_to_xy(tile_id):
        return (tile_id - 1) % GARDEN_WIDTH, (tile_id - 1) // GARDEN_WIDTH

    @staticmethod
    def tile_is_valid(pos_x, pos_y):
        return pos_x < GARDEN_WIDTH and pos_y < GARDEN_HEIGHT

    def get_tile(self, *args):
        if len(args) == 1:
            pos_x, pos_y = Field.id_to_xy(int(args[0]))
        else:
            pos_x = int(args[0])
            pos_y = int(args[1])
        if not Field.tile_is_valid(pos_x, pos_y):
            return None
        return self.garden_field[pos_y][pos_x]

    def update_tile(self, tile_id, tile_data):
        self.get_tile(tile_id).update(tile_data)


class Garden:
    _lenX = 17
    _lenY = 12
    _nMaxFields = _lenX * _lenY

    def __init__(self, garden_id):
        self.garden_id = garden_id
        self.garden_field = Field(self)

    def get_all_crops(self):
        crops = []
        for tile in self.garden_field.get_tiles_flat():
            if tile.crop not in crops:
                crops.append(tile.crop)
        return crops

    def get_crops_from_class(self, crop_class):
        return [crop for crop in self.get_all_crops() if isinstance(crop, crop_class)]

    def get_tiles_from_class(self, crop_class):
        return [tile for tile in self.garden_field.get_tiles_flat() if isinstance(tile.crop, crop_class)]

    def get_tile_ids_from_class(self, crop_class):
        return [tile.tile_id for tile in self.get_tiles_from_class(crop_class)]

    def get_tiles_to_be_watered(self):
        return list(set([crop.get_first_tile() for crop in self.get_crops_from_class(PlantCrop)
                         if not crop.is_watered()]))

    def get_harvestable_products(self):
        current_time = time.time()
        return list(set([crop.product for crop in self.get_crops_from_class(PlantCrop)
                         if crop.harvest_time < current_time]))

    def get_empty_tiles(self):
        return [tile for tile in self.garden_field.get_tiles_flat() if tile.is_empty()]

    def has_empty_tiles(self):
        return len(self.get_empty_tiles()) > 0

    def update_garden(self):
        garden_data = http_connection.get_garden_data(self.garden_id)
        for tile_id, tile_data in garden_data['garden'].items():
            self.garden_field.update_tile(tile_id, tile_data)

    def plant_fits_at(self, size, pos_x, pos_y):
        for x in range(size[0]):
            for y in range(size[1]):
                cur_x = pos_x + x
                cur_y = pos_y + y
                if not self.garden_field.tile_is_valid(cur_x, cur_y) \
                        or not self.garden_field.get_tile(cur_x, cur_y).is_empty():
                    return False
        return True

    def water_plants(self):
        """
        Ein Garten mit der gardenID wird komplett bewässert.
        """
        tiles = self.get_tiles_to_be_watered()
        for tile in tiles:
            tile_ids = [tile.tile_id for tile in tile.crop.tiles]
            http_connection.water_plant_in_garden(self.garden_id, tile.tile_id, tile_ids)

        logging.info('{} plants have been harvested in normal garden {}'.format(len(tiles), self.garden_id))
        self.update_garden()

    def harvest(self):
        """
        Erntet alles im Garten.
        """
        http_connection.harvest_garden(self.garden_id)
        self.update_garden()


class AquaGarden(Garden):

    def __init__(self):
        Garden.__init__(self, 101)

    def water_plants(self):
        """
        Alle Pflanzen im Wassergarten werden bewässert.
        """
        plants = http_connection.get_plants_to_water_in_aqua_garden()
        nPlants = len(plants['fieldID'])
        for i in range(0, nPlants):
            sFields = self._getAllFieldIDsFromFieldIDAndSizeAsString(plants['fieldID'][i], plants['sx'][i],
                                                                     plants['sy'][i])
            http_connection.water_plant_in_aqua_garden(plants['fieldID'][i], sFields)

        logging.info('Im Wassergarten wurden ' + str(nPlants) + ' Pflanzen gegossen.')

    def harvest(self):
        """
        Erntet alles im Wassergarten.
        """
        http_connection.harvest_aqua_garden()


class GardenManager:
    def __init__(self):
        self.gardens = []
        self.aqua_garden = None

    def init_gardens(self):
        """
        Ermittelt die Anzahl der Gärten und initialisiert alle.
        """
        self.gardens = []
        tmp_number_of_gardens = account_data.number_of_gardens
        for i in range(1, tmp_number_of_gardens + 1):
            garden = Garden(i)
            self.gardens.append(garden)
            garden.update_garden()

        if account_data.is_aqua_garden_available() is True:
            self.aqua_garden = AquaGarden()

    def get_garden_by_id(self, garden_id):
        for garden in self.gardens:
            if garden.garden_id == garden_id:
                return garden
        return None

    def get_earliest_required_action(self):
        earliest = None
        for garden in self.gardens:
            for crop in garden.get_crops_from_class(PlantCrop):
                # to group up all plants who can be harvested in a close timeframe the latest is taken
                if earliest is None or earliest - 600 > crop.harvest_time \
                        or (crop.harvest_time > earliest > crop.harvest_time - 600):
                    earliest = crop.harvest_time
                next_water_time = crop.next_water_time()
                if earliest - 600 > next_water_time or (next_water_time > earliest > next_water_time - 600):
                    earliest = next_water_time
        return earliest

    def get_empty_tiles(self):
        return [tile for garden in self.gardens for tile in garden.get_empty_tiles()]

    def has_empty_tiles(self):
        return len(self.get_empty_tiles()) > 0

    def can_be_planted_now(self, product):
        for garden in self.gardens:
            for x in range(GARDEN_WIDTH):
                for y in range(GARDEN_HEIGHT):
                    if garden.plant_fits_at(product.size, x, y):
                        return True
        return False

    def get_num_of_plantable_tiles(self):
        num_of_tiles = 0
        for garden in self.gardens:
            num_of_tiles += len(garden.get_tiles_from_class(PlantCrop))
            num_of_tiles += len(garden.get_empty_tiles())

        return num_of_tiles

    def get_crops_flat_from_class(self, crop_class):
        return [crop for garden in self.gardens for crop in garden.get_crops_from_class(crop_class)]

    def get_num_of_planted_plants(self):
        products = {}
        for crop in self.get_crops_flat_from_class(PlantCrop):
            if crop.product in products.keys():
                products[crop.product] += 1
            else:
                products[crop.product] = 1
        return [Box(product, quantity) for product, quantity in products.items()]

    def update_all(self):
        for garden in self.gardens:
            garden.update_garden()


garden_manager = GardenManager()
