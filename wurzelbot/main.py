#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 21.03.2017

@author: MrFlamez
'''
from wurzelbot.WurzelBot import WurzelBot
import os
import atexit
import logging


def initWurzelBot():
    logging.basicConfig(filename='wurzelbot.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')
    wurzel_bot = WurzelBot()

    def exit_handler():
        print("WurzelBot wird heruntergefahren...")
        wurzel_bot.exitBot()

    atexit.register(exit_handler)
    return wurzel_bot

#TODO: Konstruktor prüfen, evtl um Accountdaten erweitern