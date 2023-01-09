#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 21.03.2017

@author: MrFlamez
'''
from wurzelbot.WurzelBot import WurzelBot
import sys
import os
import logging
import signal


def initWurzelBot(user_name, password, server):
    logging_level_env_var = os.environ.get('WURZELBOT_LOGGING_LEVEL')
    if str(logging_level_env_var).lower() == "debug":
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    logging_message_time = os.environ.get('WURZELBOT_LOGGING_MSG_TIME')
    if logging_message_time is None or not logging_message_time:
        logging_format = '%(message)s'
    else:
        logging_format = '%(asctime)s - %(message)s'

    logging.basicConfig(stream=sys.stdout, level=logging_level, format=logging_format)
    logging.info('-------------------------------------------')
    logging.info('booting wurzelbot')
    wurzel_bot = WurzelBot(user_name, password, server)

    signal.signal(signal.SIGINT, wurzel_bot.send_termination)
    signal.signal(signal.SIGTERM, wurzel_bot.send_termination)
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
    wurzel_bot.run_objectives()


if __name__ == "__main__":
    main()
