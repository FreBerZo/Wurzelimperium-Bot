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
from wurzelbot.Produktdaten import product_data, Category
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

        product_data.init_products()

        try:
            garden_manager.init_gardens()
        except:
            logging.error('Anzahl der Gärten konnte nicht ermittelt werden.')

        spieler.accountLogin = loginDaten
        storage.update_storage()

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

    def sleep_bot_until_next_action(self):
        sleep_time = garden_manager.get_earliest_required_action() - int(time.time())
        if sleep_time <= 0:
            return
        self.exitBot()
        logging.info("Bot schläft für " + str(datetime.timedelta(seconds=sleep_time)))
        time.sleep(sleep_time)
        self.launchBot()

    def auto_plant(self):
        while True:
            collector.collect_daily_login_bonus()
            garden_manager.harvest()
            if garden_manager.has_empty_tiles():
                storage.print()
                while garden_manager.has_empty_tiles():
                    stock = garden_manager.get_potential_plants()
                    if len(stock) == 0:
                        logging.info("Das Lager ist leer.")
                        break
                    plant = None
                    for product in stock:
                        if garden_manager.can_be_planted_now(product) and product.name != "Weihnachtskaktus":
                            plant = product
                            break
                    if plant is None:
                        break
                    garden_manager.plant(plant)
                garden_manager.water()

            self.sleep_bot_until_next_action()

    # TODO: Move this to Messenger
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
