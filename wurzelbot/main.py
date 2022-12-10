#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 21.03.2017

@author: MrFlamez
'''
from wurzelbot.WurzelBot import WurzelBot
import sys
import os
import atexit
import logging


def initWurzelBot(user_name, password, server):
    # logging.basicConfig( level=logging.DEBUG, format='%(asctime)s - %(message)s')
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(message)s')
    logging.info('-------------------------------------------')
    logging.info('Starte Wurzelbot')
    wurzel_bot = WurzelBot(user_name, password, server)

    def exit_handler():
        wurzel_bot.exitBot()
        logging.info('Beende Wurzelbot')

    atexit.register(exit_handler)
    return wurzel_bot


def main():
    user = os.environ.get('WURZELBOT_USER')
    pw = os.environ.get('WURZELBOT_PW')
    server = os.environ.get('WURZELBOT_SERVER')

    if user is None or pw is None or server is None:
        logging.error("Environment variables WURZELBOT_USER, WURZELBOT_PW or WURZELBOT_SERVER are missing.")
        return

    # Login und Initialisierung des Bots
    wurzel_bot = initWurzelBot(user, pw, int(server))
    wurzel_bot.launchBot()

    # automatisches pflanzen starten
    wurzel_bot.auto_plant()


if __name__ == "__main__":
    main()
