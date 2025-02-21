"""
Created on 21.01.2017

@author: MrFlamez
"""

import logging
import time


class Session(object):
    """
    Die Session Klasse ist das Python-Pendant einer PHP-Session und dieser daher nachempfunden.
    """

    # Gültigkeitsdauer der Session (2 h -> 7200 s)
    __lifetime = 7200
    __lifetime_reserve = 300

    # Eine Reservezeit dient dazu, kurz vor Ende der Session rechtzeitig alle Aktionen
    # abschließen zu können

    def __init__(self):
        """
        Initialisierung aller Attribute mit einem Standardwert.
        """
        self.__logSession = logging.getLogger('bot.Session')
        self.__sessionID = None
        self.__serverURL = None
        self.__server = None
        self.__startTime = None
        self.__endTime = None

    def __isSessionTimeElapsed(self):
        """Prüft, ob die offene Session abgelaufen ist."""
        return time.time() > self.__endTime

    def isSessionValid(self):  # TODO: Prüfen wie die Methode sinnvoll eingesetzt werden kann
        """Prüft anhand verschiedener Kriterien, ob die aktuelle Session gültig ist."""
        bReturn = True
        if (self.__sessionID == None): bReturn = False
        if (self.__isSessionTimeElapsed()): bReturn = False
        return bReturn

    def openSession(self, sessionID, server, serverURL):
        """
        Anlegen einer neuen Session mit allen notwendigen Daten.
        """
        self.__sessionID = sessionID
        self.__server = server
        self.__serverURL = serverURL

        self.__startTime = time.time()
        self.__endTime = self.__startTime + (self.__lifetime - self.__lifetime_reserve)

        sID = str(self.__sessionID)
        self.__logSession.info('Session (ID: {}) geöffnet'.format(sID))

    def closeSession(self, wunr, server):
        """
        Zurücksetzen aller Informationen. Gleichbedeutend mit einem Schließen der Session.
        """
        sID = str(self.__sessionID)
        self.__sessionID = None
        self.__server = None
        self.__startTime = None
        self.__endTime = None
        self.__logSession.info('Session (ID: {}) geschlossen'.format(sID))

    def getRemainingTime(self):
        """Gibt die verbleibende Zeit zurück, bis die Session abläuft."""
        return self.__endTime - time.time()

    def getSessionID(self):
        """Gibt die Session-ID zurück."""
        return self.__sessionID

    def getServer(self):
        """Gibt die Servernummer zurück."""
        return self.__server

    def getServerURL(self):
        """Returns the server URL."""
        return self.__serverURL
