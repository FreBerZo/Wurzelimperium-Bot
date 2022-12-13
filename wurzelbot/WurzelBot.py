#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 21.03.2017

@author: MrFlamez
'''

from wurzelbot.Spieler import spieler, Login
from wurzelbot.HTTPCommunication import http_connection
from wurzelbot.Messenger import messenger
from wurzelbot.Garten import garden_manager
from wurzelbot.Lager import storage
from wurzelbot.Produktdaten import product_data
from wurzelbot.Gardener import gardener
from wurzelbot.Clock import clock
from wurzelbot.collector import collector
import datetime
import time
import logging


class WurzelBot(object):
    """
    Die Klasse WurzelBot übernimmt jegliche Koordination aller anstehenden Aufgaben.
    """
    def __init__(self, user_name, password, server):
        self.user_name = user_name
        self.password = password
        self.server = server

    def __getAllFieldIDsFromFieldIDAndSizeAsString(self, fieldID, sx, sy):
        """
        Rechnet anhand der fieldID und Größe der Pflanze (sx, sy) alle IDs aus und gibt diese als String zurück.
        """
        if (sx == '1' and sy == '1'): return str(fieldID)
        if (sx == '2' and sy == '1'): return str(fieldID) + ',' + str(fieldID + 1)
        if (sx == '1' and sy == '2'): return str(fieldID) + ',' + str(fieldID + 17)
        if (sx == '2' and sy == '2'): return str(fieldID) + ',' + str(fieldID + 1) + ',' + str(fieldID + 17) + ',' + str(fieldID + 18)
        logging.debug('Error der plantSize --> sx: ' + sx + ' sy: ' + sy)

    def __getAllFieldIDsFromFieldIDAndSizeAsIntList(self, fieldID, sx, sy):
        """
        Rechnet anhand der fieldID und Größe der Pflanze (sx, sy) alle IDs aus und gibt diese als Integer-Liste zurück.
        """
        sFields = self.__getAllFieldIDsFromFieldIDAndSizeAsString(fieldID, sx, sy)
        listFields = sFields.split(',') #Stringarray
                        
        for i in range(0, len(listFields)):
            listFields[i] = int(listFields[i])
            
        return listFields

    def launchBot(self):
        """
        Diese Methode startet und initialisiert den Wurzelbot. Dazu wird ein Login mit den
        übergebenen Logindaten durchgeführt und alles nötige initialisiert.
        """
        loginDaten = Login(server=self.server, user=self.user_name, password=self.password)

        try:
            http_connection.log_in(loginDaten)
        except:
            logging.error('Problem beim Starten des Wurzelbots.')
            return

        logging.info('Login erfolgreich.')

        try:
            spieler.load_user_data()
        except:
            logging.error('UserDaten konnten nicht aktualisiert werden')

        clock.init_time(spieler.time)

        spieler.load_stats()
        
        try:
            tmpHoneyFarmAvailability = http_connection.is_honey_farm_available(spieler.level)
        except:
            logging.error('Verfügbarkeit der Imkerei konnte nicht ermittelt werden.')
        else:
            spieler.setHoneyFarmAvailability(tmpHoneyFarmAvailability)

        try:
            tmpAquaGardenAvailability = http_connection.is_aqua_garden_available(spieler.level)
        except:
            logging.error('Verfügbarkeit des Wassergartens konnte nicht ermittelt werden.')
        else:
            spieler.setAquaGardenAvailability(tmpAquaGardenAvailability)

        product_data.initAllProducts()

        try:
            garden_manager.init_gardens()
        except:
            logging.error('Anzahl der Gärten konnte nicht ermittelt werden.')
 
        spieler.accountLogin = loginDaten
        storage.initProductList(product_data.getListOfAllProductIDs())
        storage.updateNumberInStock()

    def exitBot(self):
        """
        Diese Methode beendet den Wurzelbot geordnet und setzt alles zurück.
        """
        try:
            http_connection.log_out()
        except:
            logging.error('Wurzelbot konnte nicht korrekt beendet werden.')
        else:
            logging.info('Logout erfolgreich.')

    def sec_until_next_action(self):
        earliest_action = garden_manager.get_earliest_required_action()
        return earliest_action - clock.get_current_game_time()

    def auto_plant(self):
        while True:
            collector.collect_daily_login_bonus()
            self.harvestAllGarden()
            if self.hasEmptyFields():
                self.printStock()
                while self.hasEmptyFields():
                    stock = storage.getOrderedStockList()
                    plant_name = None
                    for product_id in stock:
                        product = product_data.getProductByID(product_id)
                        if gardener.can_be_planted_now(product) and product.getName() != "Weihnachtskaktus":
                            plant_name = product.getName()
                            break
                    logging.info(plant_name + " wird angepflanzt")
                    self.growPlantsInGardens(plant_name)
                logging.info("Pflanzen werden gegossen")
                self.waterPlantsInAllGardens()

            sleep_time = self.sec_until_next_action()
            if sleep_time > 0:
                self.exitBot()
                logging.info("Bot schläft für " + str(datetime.timedelta(seconds=sleep_time)))
                time.sleep(sleep_time)
                self.launchBot()

    def waterPlantsInAllGardens(self):
        """
        Alle Gärten des Spielers werden komplett bewässert.
        """
        for garden in garden_manager.gardens:
            garden.waterPlants()
        
        if spieler.is_aqua_garden_available():
            pass
            #self.waterPlantsInAquaGarden()

    def writeMessagesIfMailIsConfirmed(self, recipients, subject, body):
        """
        Erstellt eine neue Nachricht, füllt diese aus und verschickt sie.
        recipients muss ein Array sein!.
        Eine Nachricht kann nur verschickt werden, wenn die E-Mail Adresse bestätigt ist.
        """
        if (spieler.isEMailAdressConfirmed()):
            try:
                messenger.writeMessage(spieler.user_name, recipients, subject, body)
            except:
                logging.error('Konnte keine Nachricht verschicken.')
            else:
                pass

    def getEmptyFieldsOfGardens(self):
        """
        Gibt alle leeren Felder aller normalen Gärten zurück.
        Kann dazu verwendet werden zu entscheiden, wie viele Pflanzen angebaut werden können.
        """
        emptyFields = []
        try:
            for garden in garden_manager.gardens:
                emptyFields.append(garden.getEmptyFields())
        except:
            logging.error('Konnte leere Felder von Garten ' + str(garden.getID()) + ' nicht ermitteln.')
        else:
            pass
        return emptyFields

    def hasEmptyFields(self):
        emptyFields = self.getEmptyFieldsOfGardens()
        amount = 0
        for garden in emptyFields:
            amount += len(garden)

        return amount > 0

    def getWeedFieldsOfGardens(self):
        """
        Gibt alle Unkrau-Felder aller normalen Gärten zurück.
        """
        weedFields = []
        try:
            for garden in garden_manager.gardens:
                weedFields.append(garden.getWeedFields())
        except:
            logging.error('Konnte Unkraut-Felder von Garten ' + str(garden.getID()) + ' nicht ermitteln.')
        else:
            pass

        return weedFields
        
    def harvestAllGarden(self):
        #TODO: Wassergarten ergänzen
        try:
            for garden in garden_manager.gardens:
                garden.harvest()
                
            if spieler.is_aqua_garden_available():
                pass#self.waterPlantsInAquaGarden()

            storage.updateNumberInStock()
        except:
            logging.error('Konnte nicht alle Gärten ernten.')
        else:
            logging.info('Konnte alle Gärten ernten.')
            pass

    def growPlantsInGardens(self, productName, amount=-1):
        """
        Pflanzt so viele Pflanzen von einer Sorte wie möglich über alle Gärten hinweg an.
        """
        planted = 0

        product = product_data.getProductByName(productName)

        if product is None:
            logging.error('Pflanze "' + productName + '" nicht gefunden')
            return -1

        if not product.isPlant() or not product.isPlantable():
            logging.error('"' + productName + '" kann nicht angepflanzt werden')
            return -1

        for garden in garden_manager.gardens:
            if amount == -1 or amount > storage.getStockByProductID(product.getID()):
                amount = storage.getStockByProductID(product.getID())
            planted += garden.grow_plant(product.getID(), product.getSX(), product.getSY(), amount)
        
        storage.updateNumberInStock()

        return planted

    def printStock(self):
        isSmthPrinted = False
        for productID in storage.getKeys():
            product = product_data.getProductByID(productID)
            
            amount = storage.getStockByProductID(productID)
            if amount == 0: continue
            
            print(str(product.getName()).ljust(30) + 'Amount: ' + str(amount).rjust(5))
            isSmthPrinted = True
    
        if not isSmthPrinted:
            print('Your stock is empty')

    def getLowestStockEntry(self):
        entryID = storage.getLowestStockEntry()
        if entryID == -1: return 'Your stock is empty'
        return product_data.getProductByID(entryID).getName()

    def getOrderedStockList(self):
        orderedList = ''
        for productID in storage.getOrderedStockList():
            orderedList += str(product_data.getProductByID(productID).getName()).ljust(20)
            orderedList += str(storage.getOrderedStockList()[productID]).rjust(5)
            orderedList += str('\n')
        return orderedList.strip()
    
    def getLowestPlantStockEntry(self):
        lowestStock = -1
        lowestProductId = -1
        for productID in storage.getOrderedStockList():
            if not product_data.getProductByID(productID).isPlant() or \
               not product_data.getProductByID(productID).isPlantable():
                continue

            currentStock = storage.getStockByProductID(productID)
            if lowestStock == -1 or currentStock < lowestStock:
                lowestStock = currentStock
                lowestProductId = productID
                continue

        if lowestProductId == -1: return 'Your stock is empty'
        return product_data.getProductByID(lowestProductId).getName()

    def printProductDetails(self):
        product_data.printAll()
    
    def printPlantDetails(self):
        product_data.printAllPlants()
