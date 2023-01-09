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
from wurzelbot.gardener import gardener
from wurzelbot.Lager import storage
from wurzelbot.Produktdaten import product_data
from wurzelbot.collector import collector
from wurzelbot.Marktplatz import trader
from wurzelbot.objective import objective_manager
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

        http_connection.log_in(loginDaten)
        logging.debug('login successfull')
        logging.debug('loading data...')

        spieler.load_user_data()

        spieler.load_stats()

        tmpHoneyFarmAvailability = http_connection.is_honey_farm_available(spieler.level)
        spieler.setHoneyFarmAvailability(tmpHoneyFarmAvailability)

        tmpAquaGardenAvailability = http_connection.is_aqua_garden_available(spieler.level)
        spieler.setAquaGardenAvailability(tmpAquaGardenAvailability)

        product_data.init_products()

        garden_manager.init_gardens()

        spieler.accountLogin = loginDaten
        storage.load_storage(efficient_load=False)
        trader.load_wimp_data()
        logging.debug('loading successfull')

    def exitBot(self):
        """
        Diese Methode beendet den Wurzelbot geordnet und setzt alles zurück.
        """
        http_connection.log_out()
        logging.info('logout successfull')

    def sleep_bot_until_next_action(self):
        sleep_time = garden_manager.get_earliest_required_action() - int(time.time())
        if sleep_time <= 0:
            return
        self.exitBot()
        logging.info("bot sleeps for " + str(datetime.timedelta(seconds=sleep_time)))
        time.sleep(sleep_time)
        self.launchBot()

    def run_objectives(self):
        while True:
            collector.collect_daily_login_bonus()

            gardener.harvest()

            objective_finished = True
            while objective_finished:
                objective_manager.create_objectives()
                objective_finished = objective_manager.run_objectives()

            gardener.water()

            # trader.reject_bad_wimp_offers()

            self.sleep_bot_until_next_action()

    def auto_plant(self):
        while True:
            collector.collect_daily_login_bonus()
            gardener.harvest()
            if garden_manager.has_empty_tiles():
                storage.print()
                while garden_manager.has_empty_tiles():
                    stock = gardener.get_potential_plants()
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
                    gardener.plant(plant)
            gardener.water()

            trader.reject_bad_wimp_offers()

            self.sleep_bot_until_next_action()

    # TODO: Move this to Messenger
    def writeMessagesIfMailIsConfirmed(self, recipients, subject, body):
        """
        Erstellt eine neue Nachricht, füllt diese aus und verschickt sie.
        recipients muss ein Array sein!.
        Eine Nachricht kann nur verschickt werden, wenn die E-Mail Adresse bestätigt ist.
        """
        if (spieler.isEMailAdressConfirmed()):
            messenger.writeMessage(spieler.user_name, recipients, subject, body)
