"""
Created on 21.03.2017

@author: MrFlamez
"""
import datetime
import logging
import sys
import time

from wurzelbot.account_data import AccountData, Login
from wurzelbot.collector import Collector
from wurzelbot.communication.http_communication import HTTPConnection
from wurzelbot.gardens.garden_helper import GardenHelper
from wurzelbot.gardens.gardener import Gardener
from wurzelbot.gardens.gardens import GardenManager
from wurzelbot.objectives.objective_manager import ObjectiveManager
from wurzelbot.product.product_data import ProductData
from wurzelbot.product.storage import Storage
from wurzelbot.trading.market import Market
from wurzelbot.trading.trader import Trader


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
        # TODO: tidy up this method, maybe make loader class
        """
        Diese Methode startet und initialisiert den Wurzelbot. Dazu wird ein Login mit den
        übergebenen Logindaten durchgeführt und alles nötige initialisiert.
        """

        login_data = Login(server=self.server, user=self.user_name, password=self.password)

        retries = 3
        while not HTTPConnection().check_server_status(self.server):
            retries -= 1
            if retries < 1:
                raise ConnectionError("server has internal error")
            logging.info("server internal error")
            logging.info("retrying in 30 minutes")
            time.sleep(1800)

        HTTPConnection().log_in(login_data)
        logging.debug('login successfull')
        logging.debug('loading data...')

        old_level = AccountData().level
        AccountData().load_user_data()

        new_level = AccountData().level
        # in case of level up, recalculate the most profitable product
        if old_level is not None and old_level < new_level:
            Market().dispose_profitability()

        AccountData().load_stats()

        AccountData().load_garden_availability()

        ProductData().init_products()

        GardenManager().init_gardens()

        Storage().load_storage(efficient_load=False)
        Market().load_wimp_data()
        logging.debug('loading successfull')

    def exit_bot(self):
        """
        Diese Methode beendet den Wurzelbot geordnet und setzt alles zurück.
        """
        if HTTPConnection().logged_in:
            HTTPConnection().log_out()
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
        sleep_time = GardenManager().get_earliest_required_action() - int(time.time())
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

            Collector.collect_daily_login_bonus()

            self.check_termination()

            Gardener.harvest()

            self.check_termination()

            objective_finished = True
            while objective_finished:
                ObjectiveManager().create_objectives()
                self.check_termination()
                objective_finished = ObjectiveManager().run_objectives()
                self.check_termination()

            self.check_termination()

            Gardener.water()

            # trader.reject_bad_wimp_offers()

            self.check_termination()

            self.sleep_bot_until_next_action()

    def auto_plant(self):
        while True:
            Collector.collect_daily_login_bonus()
            Gardener.harvest()
            if GardenManager().has_empty_tiles():
                Storage().print()
                while GardenManager().has_empty_tiles():
                    stock = GardenHelper.get_potential_plants()
                    if len(stock) == 0:
                        logging.info("Das Lager ist leer.")
                        break
                    plant = None
                    for product in stock:
                        if GardenManager().can_be_planted_now(product) and product.name != "Weihnachtskaktus":
                            plant = product
                            break
                    if plant is None:
                        break
                    Gardener.plant(plant)
            Gardener.water()

            Trader.reject_bad_wimp_offers()

            self.sleep_bot_until_next_action()
