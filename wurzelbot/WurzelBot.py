"""
Created on 21.03.2017

@author: MrFlamez
"""
import datetime
import logging
import sys
import time

from wurzelbot.account_data import account_data, Login
from wurzelbot.collector import collector
from wurzelbot.communication.http_communication import http_connection
from wurzelbot.gardens.gardener import gardener
from wurzelbot.gardens.gardens import garden_manager
from wurzelbot.objectives.objective_manager import objective_manager
from wurzelbot.product.product_data import product_data
from wurzelbot.product.storage import storage
from wurzelbot.trading.trader import trader


class WurzelBot:
    """
    Die Klasse WurzelBot übernimmt jegliche Koordination aller anstehenden Aufgaben.
    """

    def __init__(self, user_name, password, server):
        self.user_name = user_name
        self.password = password
        self.server = server
        self.sleeping = False
        self.terminating = False

    def init_bot(self):
        # TODO: tidy up this method
        """
        Diese Methode startet und initialisiert den Wurzelbot. Dazu wird ein Login mit den
        übergebenen Logindaten durchgeführt und alles nötige initialisiert.
        """

        login_data = Login(server=self.server, user=self.user_name, password=self.password)

        http_connection.log_in(login_data)
        logging.debug('login successfull')
        logging.debug('loading data...')

        account_data.load_user_data()

        account_data.load_stats()

        honey_farm_availability = http_connection.is_honey_farm_available(account_data.level)
        account_data.setHoneyFarmAvailability(honey_farm_availability)

        aqua_garden_availability = http_connection.is_aqua_garden_available(account_data.level)
        account_data.setAquaGardenAvailability(aqua_garden_availability)

        product_data.init_products()

        garden_manager.init_gardens()

        account_data.account_login = login_data
        storage.load_storage(efficient_load=False)
        trader.load_wimp_data()
        logging.debug('loading successfull')

    def exit_bot(self):
        """
        Diese Methode beendet den Wurzelbot geordnet und setzt alles zurück.
        """
        if http_connection.logged_in:
            http_connection.log_out()
            logging.info('logout successfull')

    def send_termination(self, *args):
        if self.sleeping:
            self.terminate()
        self.terminating = True
        logging.info("planned shutdown")

    def check_termination(self):
        if self.terminating:
            self.terminate()

    def terminate(self):
        self.exit_bot()
        logging.info('shutting down wurzelbot')
        sys.exit()

    # TODO: make a new class of this. optimize loading: not everything requires to be loaded again.
    #  add scheduling when the bot should be woken up
    def sleep_bot_until_next_action(self):
        sleep_time = garden_manager.get_earliest_required_action() - int(time.time())
        if sleep_time <= 0:
            return
        self.exit_bot()
        logging.info("bot sleeps for " + str(datetime.timedelta(seconds=sleep_time)))
        self.sleeping = True
        time.sleep(sleep_time)
        self.sleeping = False
        self.init_bot()

    def run_objectives(self):
        while True:
            self.check_termination()

            collector.collect_daily_login_bonus()

            self.check_termination()

            gardener.harvest()

            self.check_termination()

            objective_finished = True
            while objective_finished:
                objective_manager.create_objectives()
                self.check_termination()
                objective_finished = objective_manager.run_objectives()
                self.check_termination()

            self.check_termination()

            gardener.water()

            # trader.reject_bad_wimp_offers()

            self.check_termination()

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
