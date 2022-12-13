#!/usr/bin/env python
# -*- coding: utf-8 -*-

from wurzelbot.HTTPCommunication import http_connection
from wurzelbot.Produktdaten import product_data
from wurzelbot.Spieler import spieler
import logging

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
    def __init__(self, x, y, tile_id, garden_id):
        self.pos_x = x
        self.pos_y = y
        self.tile_id = tile_id
        self.garden_id = garden_id
        self.crop = None

    def set_crop(self, crop):
        if self.crop is not None:
            del self.crop
        self.crop = crop

    def is_empty(self):
        return self.crop is None

    def update(self, tile_data):
        width, height = str(tile_data[9]).split('x')[:2]
        size = (int(width), int(height))

        # a crop that spans multiple tiles will only be updated at the last tile of the crop
        x_pos = int(tile_data[1])
        y_pos = int(tile_data[2])
        if (size[0], size[1]) != (x_pos, y_pos):
            return

        if size[0] > 1 or size[1] > 1:
            garden = garden_manager.get_garden_by_id(self.garden_id)
            tile_list = []
            for y in range(size[1], 0, -1):
                for x in range(size[0], 0, -1):
                    tile_list.append(garden.garden_field.get_tile(self.pos_x + 1 - x, self.pos_y + 1 - y))
        else:
            tile_list = [self]

        crop_id = int(tile_data[0])
        if crop_id == 0:
            crop = None  # empty
        elif crop_id in [41, 42, 43, 45]:
            crop = WeedCrop(crop_id, float(tile_data[6]), size, tile_list)
        else:
            product = product_data.getProductByID(crop_id)
            if product.isPlant():
                crop = PlantCrop(product, int(tile_data[3]), int(tile_data[4]), size, int(tile_data[10]), tile_list)
            elif product.isDecoration():
                crop = DecorationCrop(product, size, tile_list)
            else:
                crop = None

        for tile in tile_list:
            tile.set_crop(crop)


class Field:

    garden_field = []

    def __init__(self, garden_id):
        self.garden_id = garden_id

        i = 1
        for y in range(GARDEN_HEIGHT):
            self.garden_field.append([])
            for x in range(GARDEN_WIDTH):
                self.garden_field[y].append(Tile(x, y, i, garden_id))
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
        self.garden_field = Field(garden_id)

    def _getAllFieldIDsFromFieldIDAndSizeAsString(self, fieldID, sx, sy):
        """
        Rechnet anhand der fieldID und Größe der Pflanze (sx, sy) alle IDs aus und gibt diese als String zurück.
        """
        
        # Zurückgegebene Felderindizes (x) für Pflanzen der Größe 1-, 2- und 4-Felder.
        # Wichtig beim Gießen; dort müssen alle Indizes angegeben werden.
        # (Sowohl die mit x als auch die mit o gekennzeichneten).
        # x: fieldID
        # o: ergänzte Felder anhand der size
        # +---+   +---+---+   +---+---+
        # | x |   | x | o |   | x | o |
        # +---+   +---+---+   +---+---+
        #                     | o | o |
        #                     +---+---+
        
        if (sx == 1 and sy == 1): return str(fieldID)
        if (sx == 2 and sy == 1): return str(fieldID) + ',' + str(fieldID + 1)
        if (sx == 1 and sy == 2): return str(fieldID) + ',' + str(fieldID + 17)
        if (sx == 2 and sy == 2): return str(fieldID) + ',' + str(fieldID + 1) + ',' + str(fieldID + 17) + ',' + str(fieldID + 18)
        logging.debug('Error der plantSize --> sx: ' + str(sx) + ' sy: ' + str(sy))

    def _getAllFieldIDsFromFieldIDAndSizeAsIntList(self, fieldID, sx, sy):
        """
        Rechnet anhand der fieldID und Größe der Pflanze (sx, sy) alle IDs aus und gibt diese als Integer-Liste zurück.
        """
        sFields = self._getAllFieldIDsFromFieldIDAndSizeAsString(fieldID, sx, sy)
        listFields = sFields.split(',') #Stringarray
                        
        for i in range(0, len(listFields)):
            listFields[i] = int(listFields[i])
            
        return listFields
    
    def _isPlantGrowableOnField(self, fieldID, emptyFields, fieldsToPlant, sx):
        """
        Prüft anhand mehrerer Kriterien, ob ein Anpflanzen möglich ist.
        """
        # Betrachtetes Feld darf nicht besetzt sein
        if not (fieldID in emptyFields): return False
        
        # Anpflanzen darf nicht außerhalb des Gartens erfolgen
        # Dabei reicht die Betrachtung in x-Richtung, da hier ein
        # "Zeilenumbruch" stattfindet. Die y-Richtung ist durch die
        # Abfrage abgedeckt, ob alle benötigten Felder frei sind.
        # Felder außerhalb (in y-Richtung) des Gartens sind nicht leer,
        # da sie nicht existieren.
        if not ((self._nMaxFields - fieldID)%self._lenX >= sx - 1): return False
        fieldsToPlantSet = set(fieldsToPlant)
        emptyFieldsSet = set(emptyFields)
        
        # Alle benötigten Felder der Pflanze müssen leer sein
        if not (fieldsToPlantSet.issubset(emptyFieldsSet)): return False
        return True

    def get_all_crops(self):
        crops = []
        for tile in self.garden_field.get_tiles_flat():
            if tile.crop not in crops:
                crops.append(tile.crop)
        return crops

    def get_all_crops_from_class(self, crop_class):
        return [crop for crop in self.get_all_crops() if isinstance(crop, crop_class)]

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

    def waterPlants(self):
        """
        Ein Garten mit der gardenID wird komplett bewässert.
        """
        logging.info('Gieße alle Pflanzen im Garten ' + str(self.garden_id) + '.')
        try:
            plants = http_connection.get_plants_to_water_in_garden(self.garden_id)
            nPlants = len(plants['fieldID'])
            for i in range(0, nPlants):
                sFields = self._getAllFieldIDsFromFieldIDAndSizeAsString(plants['fieldID'][i], plants['sx'][i], plants['sy'][i])
                http_connection.water_plant_in_garden(self.garden_id, plants['fieldID'][i], sFields)
        except:
            logging.error('Garten ' + str(self.garden_id) + ' konnte nicht bewässert werden.')
        else:
            logging.info('Im Garten ' + str(self.garden_id) + ' wurden ' + str(nPlants) + ' Pflanzen gegossen.')

        self.update_garden()

    def getEmptyFields(self):
        """
        Gibt alle leeren Felder des Gartens zurück.
        """
        try:
            tmpEmptyFields = http_connection.get_empty_fields_of_garden(self.garden_id)
        except:
            logging.error('Konnte leere Felder von Garten ' + str(self.garden_id) + ' nicht ermitteln.')
        else:
            return tmpEmptyFields

    def getWeedFields(self):
        """
        Gibt alle Unkraut-Felder des Gartens zurück.
        """
        try:
            tmpWeedFields = http_connection.get_weed_fields_of_garden(self.garden_id)
        except:
            logging.error('Konnte leere Felder von Garten ' + str(self.garden_id) + ' nicht ermitteln.')
        else:
            return tmpWeedFields

    def harvest(self):
        """
        Erntet alles im Garten.
        """
        try:
            http_connection.harvest_garden(self.garden_id)
        except:
            raise
        else:
            pass

        self.update_garden()

    def growPlant(self, plantID, sx, sy, amount):
        """
        Pflanzt eine Pflanze beliebiger Größe an.
        """
  
        planted = 0
        emptyFields = self.getEmptyFields()
        
        try:
            for field in range(1, self._nMaxFields + 1):
                if planted == amount: break
            
                fieldsToPlant = self._getAllFieldIDsFromFieldIDAndSizeAsIntList(field, sx, sy)
            
                if (self._isPlantGrowableOnField(field, emptyFields, fieldsToPlant, sx)):
                    fields = self._getAllFieldIDsFromFieldIDAndSizeAsString(field, sx, sy)
                    http_connection.grow_plant(field, plantID, self.garden_id, fields)
                    planted += 1

                    #Nach dem Anbau belegte Felder aus der Liste der leeren Felder loeschen
                    fieldsToPlantSet = set(fieldsToPlant)
                    emptyFieldsSet = set(emptyFields)
                    tmpSet = emptyFieldsSet - fieldsToPlantSet
                    emptyFields = list(tmpSet)

        except:
            logging.error('Im Garten ' + str(self.garden_id) + ' konnte nicht gepflanzt werden.')
            return 0
        else:
            logging.info('Im Garten ' + str(self.garden_id) + ' wurden ' + str(planted) + ' Pflanzen gepflanzt.')
            return planted


class AquaGarden(Garden):
    
    def __init__(self):
        Garden.__init__(self, 101)


    def waterPlants(self):
        """
        Alle Pflanzen im Wassergarten werden bewässert.
        """
        try:
            plants = http_connection.get_plants_to_water_in_aqua_garden()
            nPlants = len(plants['fieldID'])
            for i in range(0, nPlants):
                sFields = self._getAllFieldIDsFromFieldIDAndSizeAsString(plants['fieldID'][i], plants['sx'][i], plants['sy'][i])
                http_connection.water_plant_in_aqua_garden(plants['fieldID'][i], sFields)
        except:
            logging.error('Wassergarten konnte nicht bewässert werden.')
        else:
            logging.info('Im Wassergarten wurden ' + str(nPlants) + ' Pflanzen gegossen.')
        
    def harvest(self):
        """
        Erntet alles im Wassergarten.
        """
        try:
            http_connection.harvest_aqua_garden()
        except:
            raise
        else:
            pass


class GardenManager:
    def __init__(self):
        self.gardens = []
        self.aqua_garden = None

    def init_gardens(self):
        """
        Ermittelt die Anzahl der Gärten und initialisiert alle.
        """
        self.gardens = []
        tmp_number_of_gardens = spieler.get_number_of_gardens()
        for i in range(1, tmp_number_of_gardens + 1):
            garden = Garden(i)
            self.gardens.append(garden)
            garden.update_garden()

        if spieler.is_aqua_garden_available() is True:
            self.aqua_garden = AquaGarden()

    def get_garden_by_id(self, garden_id):
        for garden in self.gardens:
            if garden.garden_id == garden_id:
                return garden
        return None

    def get_earliest_required_action(self):
        earliest = None
        for garden in self.gardens:
            for crop in garden.get_all_crops_from_class(PlantCrop):
                # to group up all plants who can be harvested in a close timeframe the latest is taken
                if earliest is None or earliest - 60 > crop.harvest_time \
                        or (crop.harvest_time > earliest > crop.harvest_time - 60):
                    earliest = crop.harvest_time
        return earliest

    def update_all(self):
        for garden in self.gardens:
            garden.update_garden()


garden_manager = GardenManager()
