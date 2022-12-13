#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 21.03.2017
@author: MrFlamez
'''
import logging
import re

from wurzelbot.HTTPCommunication import http_connection
from collections import namedtuple


Login = namedtuple('Login', 'server user password')

class Spieler():
    """
    Diese Daten-Klasse enthält alle wichtigen Informationen über den Spieler.
    """
    
    accountLogin = None
    __userName = None
    __userID = None
    numberOfGardens = None
    # TODO: make attributes for every piece of required data instead of raw data
    raw_user_data = None
    raw_stats = None
    __honeyFarmAvailability = None
    __aquaGardenAvailability = None
    __eMailAdressConfirmed = None

    def __init__(self):
        pass

    def setHoneyFarmAvailability(self, bAvl):
        self.__honeyFarmAvailability = bAvl

    def isHoneyFarmAvailable(self):
        return self.__honeyFarmAvailability

    def setAquaGardenAvailability(self, bAvl):
        self.__aquaGardenAvailability = bAvl

    def is_aqua_garden_available(self):
        return self.__aquaGardenAvailability
    
    def isEMailAdressConfirmed(self):
        return self.__eMailAdressConfirmed
    
    def getUserName(self):
        return re.findall(r'<td>(.+?)</td>', self.raw_stats['table'][0])[1].replace(r'&nbsp;', '')
    
    def getLevelNr(self):
        return int(self.raw_user_data['levelnr'])

    def getLevelName(self):
        return str(self.raw_user_data['level'])
    
    def getBar(self):
        return str(self.raw_user_data['bar'])
    
    def getPoints(self):
        return int(self.raw_user_data['points'])

    def getCoins(self):
        return int(self.raw_user_data['coins'])

    def get_time(self):
        return int(self.raw_user_data['time'])

    def get_number_of_gardens(self):
        return int(re.findall(r'<td>(.+?)</td>', self.raw_stats['table'][16])[1].replace(r'&nbsp;', ''))

    def get_daily_login_bonus(self):
        return self.raw_user_data['dailyloginbonus']
    
    def setUserDataFromServer(self):
        """
        Liest den Spielerdaten vom Server und speichert sie in der Klasse.
        """
        try:
            tmpUserData = http_connection.read_user_data_from_server()
        except:

            logging.warning('Status der E-Mail Adresse konnte nicht ermittelt werden.')
        else:
            self.raw_user_data = tmpUserData

    def set_stats_from_server(self):
        self.raw_stats = http_connection.get_stats()

    def setUserID(self, userID):
        self.__userID = userID
        
    def setConfirmedEMailAdressFromServer(self, http):
        """
        Liest vom Server, ob die E-Mail Adresse bestätigt ist und speichert den Status in der KLasse.
        """
        try:
            tmpEMailConf = http.check_if_email_address_is_confirmed()
        except:
            pass
        else:
            self.__eMailAdressConfirmed = tmpEMailConf
            

spieler = Spieler()
