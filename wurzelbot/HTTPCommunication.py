#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 21.03.2017

@author: MrFlamez
'''

from urllib.parse import urlencode
import json, re, httplib2, yaml, time, logging, math, io
from http.cookies import SimpleCookie
from wurzelbot.Session import Session
from lxml import html, etree

# Defines
HTTP_STATE_OK = 200
HTTP_STATE_FOUND = 302  # moved temporarily
SERVER_DOMAIN = 'wurzelimperium.de'


class HTTPConnection(object):
    """Mit der Klasse HTTPConnection werden alle anfallenden HTTP-Verbindungen verarbeitet."""

    def __init__(self):
        self.__webclient = httplib2.Http(disable_ssl_certificate_validation=True)
        self.__webclient.follow_redirects = False
        self.__userAgent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36 Vivaldi/2.2.1388.37'
        self.__Session = Session()
        self.__token = None
        self.__userID = None
        self.__cookie = None
        self.__unr = None
        self.__portunr = None

    def __del__(self):
        self.__Session = None
        self.__token = None
        self.__userID = None
        self.__unr = None
        self.__portunr = None

    ############################
    # General helper functions #
    ############################
    def __send_request(self, address, method='GET', body=None, headers=None):
        url = self.__get_url() + address
        if headers is None:
            headers = self.__get_header()
        else:
            headers = {**self.__get_header(), **headers}
        try:
            return self.__webclient.request(url, method, body, headers)
        except:
            raise

    def __get_header(self):
        headers = {'Cookie': 'PHPSESSID={};wunr={}'.format(self.__Session.getSessionID(), self.__userID),
                   'Connection': 'Keep-Alive'}
        return headers

    def __get_url(self):
        return 'http://s{}.{}/'.format(self.__Session.getServer(), SERVER_DOMAIN)

    def __check_http_ok(self, response):
        """Prüft, ob der Status der HTTP Anfrage OK ist."""
        if not (response['status'] == str(HTTP_STATE_OK)):
            logging.debug('HTTP State: ' + str(response['status']))
            raise HTTPStateError('HTTP Status ist nicht OK')

    def __check_http_found(self, response):
        """Prüft, ob der Status der HTTP Anfrage FOUND ist."""
        if not (response['status'] == str(HTTP_STATE_FOUND)):
            logging.debug('HTTP State: ' + str(response['status']))
            raise HTTPStateError('HTTP Status ist nicht FOUND')

    def __generate_json_and_check_success(self, content):
        """Aufbereitung und Prüfung der vom Server empfangenen JSON Daten."""
        j_content = json.loads(content)
        if j_content['success'] == 1:
            return j_content
        else:
            raise JSONError()

    def __generate_json_and_check_ok(self, content: str):
        """Aufbereitung und Prüfung der vom Server empfangenen JSON Daten."""
        j_content = json.loads(content)
        if j_content['status'] == 'ok':
            return j_content
        else:
            raise JSONError()

    def __get_token_from_url(self, url):
        """Ermittelt aus einer übergebenen URL den security token."""
        split = re.search(r'https://.*/logw.php.*token=([a-f0-9]{32})', url)
        iErr = 0
        tmpToken = ''
        if split:
            tmpToken = split.group(1)
            if tmpToken == '':
                iErr = 1
        else:
            iErr = 1

        if iErr == 1:
            logging.debug(tmpToken)
            raise JSONError('Fehler bei der Ermittlung des tokens')
        else:
            self.__token = tmpToken

    def __get_token_from_url_port(self, url):
        """Ermittelt aus einer übergebenen URL den security token."""
        split = re.search(r'.*portal/port_logw.php.*token=([a-f0-9]{32})', url)
        iErr = 0
        tmpToken = ''
        if split:
            tmpToken = split.group(1)
            if (tmpToken == ''):
                iErr = 1
        else:
            iErr = 1

        if (iErr == 1):
            logging.debug(tmpToken)
            raise JSONError('Fehler bei der Ermittlung des tokens')
        else:
            self.__token = tmpToken

    def __get_unr_from_url_port(self, url):
        """Ermittelt aus einer übergebenen URL den security token."""
        split = re.search(r'.*portal/port_logw.php.*unr=([a-f0-9]{6}).*port', url)
        iErr = 0
        tmpunr = ''
        if split:
            tmpunr = split.group(1)
            if (tmpunr == ''):
                iErr = 1
        else:
            iErr = 1

        if (iErr == 1):
            logging.debug(tmpunr)
            raise JSONError(f'Fehler bei der Ermittlung des tokens')
        else:
            self.__unr = tmpunr

    def __get_port_unr_from_url_port(self, url):
        """Ermittelt aus einer übergebenen URL den security token."""
        split = re.search(r'.*portal/port_logw.php.*portunr=([a-f0-9]{7})', url)
        iErr = 0
        tmpportunr = ''
        if split:
            tmpportunr = split.group(1)
            if (tmpportunr == ''):
                iErr = 1
        else:
            iErr = 1

        if (iErr == 1):
            logging.debug(tmpportunr)
            raise JSONError('Fehler bei der Ermittlung des tokens')
        else:
            self.__portunr = tmpportunr

    def __check_session_deleted(self, cookie):
        """Prüft, ob die Session gelöscht wurde."""
        if not (cookie['PHPSESSID'].value == 'deleted'):
            logging.debug('SessionID: ' + cookie['PHPSESSID'].value)
            raise HTTPRequestError('Session wurde nicht gelöscht')

    def __generate_yaml_content_and_check_for_success(self, content: str):
        """Aufbereitung und Prüfung der vom Server empfangenen YAML Daten auf Erfolg."""
        content = content.replace('\n', ' ')
        content = content.replace('\t', ' ')
        yContent = yaml.load(content, Loader=yaml.FullLoader)

        if yContent['success'] != 1:
            raise YAMLError()

    def __generate_yaml_content_and_check_status_for_ok(self, content):
        """Aufbereitung und Prüfung der vom Server empfangenen YAML Daten auf iO Status."""
        content = content.replace('\n', ' ')
        content = content.replace('\t', ' ')
        yContent = yaml.load(content, Loader=yaml.FullLoader)

        if yContent['status'] != 'ok':
            raise YAMLError()

    # general actions
    def log_in(self, loginDaten):
        """Führt einen login durch und öffnet eine Session."""
        parameter = urlencode({'do': 'login',
                               'server': 'server{}'.format(str(loginDaten.server)),
                               'user': loginDaten.user,
                               'pass': loginDaten.password})

        headers = {'Content-type': 'application/x-www-form-urlencoded',
                   'Connection': 'keep-alive'}

        try:
            response, content = self.__webclient.request('https://www.{}/dispatch.php'.format(SERVER_DOMAIN),
                                                         'POST',
                                                         parameter,
                                                         headers)
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            self.__get_token_from_url(jContent['url'])
            response, content = self.__webclient.request(jContent['url'], 'GET', headers=headers)
            self.__check_http_found(response)
        except:
            raise
        else:
            cookie = SimpleCookie(response['set-cookie'])
            cookie.load(str(response["set-cookie"]).replace("secure, ", "", -1))
            self.__Session.openSession(cookie['PHPSESSID'].value, str(loginDaten.server), SERVER_DOMAIN)
            self.__cookie = cookie
            self.__userID = cookie['wunr'].value

    def log_out(self):
        """Logout des Spielers inkl. Löschen der Session."""
        # TODO: Was passiert beim Logout einer bereits ausgeloggten Session
        try:  # content ist beim Logout leer
            response, content = self.__send_request('main.php?page=logout')
            self.__check_http_found(response)
            cookie = SimpleCookie(response['set-cookie'])
            self.__check_session_deleted(cookie)
        except:
            raise

    # general info
    def __get_info_from_json_content(self, jContent, info):
        """Looks up certain info in the given JSON object and returns it."""
        mapping = {
            'Username': 'table.0',
            'Gardens': 'table.16',
            'CompletedQuests': 'table.5',
            'CactusQuest': 'table.7',
            'EchinoQuest': 'table.8',
            'BigheadQuest': 'table.9',
            'OpuntiaQuest': 'table.10',
            'SaguaroQuest': 'table.11'
        }

        try:
            keys = mapping[info].split('.')
            result = jContent
            for key in keys:
                result = result[key]
            return result
        except KeyError:
            logging.debug(jContent['table'])
            raise JSONError('Info:' + info + " not found.")

    def get_info_from_stats(self, info):
        """
        Returns different parameters from user's stats'
        @param info: available values: 'Username', 'Gardens', 'CompletedQuests'
        @return: parameter value
        """
        return self.__get_info_from_json_content(self.get_stats(), info)

    def get_stats(self):
        try:
            address = 'ajax/ajax.php?do=statsGetStats&which=0&start=0' \
                      '&additional={}&token={}'.format(self.__userID, self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content.decode('UTF-8'))
        except:
            raise
        else:
            return jContent

    def read_user_data_from_server(self):
        """Ruft eine Updatefunktion im Spiel auf und verarbeitet die empfangenen userdaten."""
        try:
            response, content = self.__send_request('ajax/menu-update.php')
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_success(content)
        except:
            raise
        else:
            return jContent

    def check_if_email_address_is_confirmed(self):
        """Prüft, ob die E-Mail-Adresse im Profil bestätigt ist."""
        try:
            response, content = self.__send_request('nutzer/profil.php')
            self.__check_http_ok(response)
        except:
            raise
        else:
            result = re.search(r'Unbestätigte Email:', content)
            return result is None

    # TODO: I don't know what this is, maybe redo or remove
    def get_user_list(self, iStart, iEnd):
        """
        #TODO: finalisieren
        """
        userList = {'Nr': [], 'Gilde': [], 'Name': [], 'Punkte': []}
        # iStart darf nicht 0 sein, da sonst beim korrigierten Index -1 übergeben wird
        userList = {'Nr': [], 'Gilde': [], 'Name': [], 'Punkte': []}
        # iStart darf nicht 0 sein, da sonst beim korrigierten Index -1 übergeben wird
        if iStart <= 0:
            iStart = 1

        if iStart == iEnd or iStart > iEnd:
            return False

        iStartCorr = iStart - 1
        iCalls = int(math.ceil(float(iEnd - iStart) / 100))

        print(iCalls)
        for i in range(iCalls):
            print(i)
            try:
                address = f'ajax/ajax.php?do=statsGetStats&which=1&start={str(iStartCorr)}' \
                          f'&showMe=0&additional=0&token={self.__token}'
                response, content = self.__send_request(address)
                self.__check_http_ok(response)
                jContent = self.__generate_json_and_check_ok(content)
            except:
                raise
            else:
                try:
                    for j in jContent['table']:
                        result = re.search(
                            r'<tr><td class=".*">(.*)<\/td><td class=".*tag">(.*)<\/td><td class=".*uname">([^<]*)<.*class=".*pkt">(.*)<\/td><\/tr>',
                            j)
                        userList['Nr'].append(str(result.group(1)).replace('.', ''))
                        userList['Gilde'].append(str(result.group(2)))
                        userList['Name'].append(str(result.group(3).encode('utf-8')).replace('&nbsp;', ''))
                        userList['Punkte'].append(int(str(result.group(4).replace('.', ''))))
                except:
                    raise

            iStartCorr = iStartCorr + 100

        return userList

    ###################
    # Garden managing #
    ###################
    # normal Garden
    # TODO: check if required (should be deprecated because of new garden presentation)
    def __is_field_watered(self, jContent, fieldID):
        """
        Ermittelt, ob ein Feld fieldID gegossen ist und gibt True/False zurück.
        Ist das Datum der Bewässerung 0, wurde das Feld noch nie gegossen.
        Eine Bewässerung hält 24 Stunden an. Liegt die Zeit der letzten Bewässerung
        also 24 Stunden + 30 Sekunden (Sicherheit) zurück, wurde das Feld zwar bereits gegossen,
        kann jedoch wieder gegossen werden.
        """
        oneDayInSeconds = (24*60*60) + 30
        currentTimeInSeconds = time.time()
        waterDateInSeconds = int(jContent['water'][fieldID-1][1])

        if waterDateInSeconds == '0' or (currentTimeInSeconds - waterDateInSeconds) > oneDayInSeconds:
            return False
        else:
            return True

    # TODO: check if required (should be deprecated because of new garden presentation)
    def __find_plants_to_be_watered_from_json_content(self, jContent):
        """Sucht im JSON Content nach Pflanzen die bewässert werden können und gibt diese inkl. der Pflanzengröße zurück."""
        plantsToBeWatered = {'fieldID': [], 'sx': [], 'sy': []}
        for field in range(0, len(jContent['grow'])):
            plantedFieldID = jContent['grow'][field][0]
            plantSize = jContent['garden'][str(plantedFieldID)][9]
            splittedPlantSize = str(plantSize).split('x')
            sx = splittedPlantSize[0]
            sy = splittedPlantSize[1]
            
            if not self.__is_field_watered(jContent, plantedFieldID):
                fieldIDToBeWatered = plantedFieldID
                plantsToBeWatered['fieldID'].append(fieldIDToBeWatered)
                plantsToBeWatered['sx'].append(int(sx))
                plantsToBeWatered['sy'].append(int(sy))

        return plantsToBeWatered

    def _change_garden(self, gardenID):
        """Wechselt den Garten."""
        try:
            address = 'ajax/ajax.php?do=changeGarden&garden={}&token={}'.format(str(gardenID), self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
            self.__generate_json_and_check_ok(content)
        except:
            raise

    def get_garden_data(self, garden_id):
        """
        Gibt alle Daten zu einem Garten roh zurück.
        """
        try:
            address = 'ajax/ajax.php?do=changeGarden&garden={}&token={}'.format(str(garden_id), str(self.__token))
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
        except:
            raise
        else:
            return jContent

    def water_plant_in_garden(self, iGarten, iField, sFieldsToWater):
        """Bewässert die Pflanze iField mit der Größe sSize im Garten iGarten."""
        try:
            fields = ','.join([str(field) for field in sFieldsToWater])
            address = 'save/wasser.php?feld[]={}&felder[]={}&cid={}&garden={}'\
                      .format(str(iField), fields, self.__token, str(iGarten))
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
            self.__generate_yaml_content_and_check_for_success(content.decode('UTF-8'))
        except:
            raise

    def harvest_garden(self, gardenID):
        """Erntet alle fertigen Pflanzen im Garten."""
        try:
            self._change_garden(gardenID)
            address = 'ajax/ajax.php?do=gardenHarvestAll&token={}'.format(self.__token)
            response, content = self.__send_request(address)
            jContent = json.loads(content)

            if jContent['status'] == 'error':
                logging.info(jContent['message'])
            elif jContent['status'] == 'ok':
                msg = jContent['harvestMsg'].replace('<div>', '').replace('</div>', '\n').replace('&nbsp;', ' ')
                logging.info(msg.strip())
        except:
            raise

    def grow_plant(self, field, plant, gardenID, fields):
        """Baut eine Pflanze auf einem Feld an."""
        try:
            address = 'save/pflanz.php?pflanze[]={}&feld[]={}&felder[]={}&cid={}&garden={}'\
                      .format(str(plant), str(field), ','.join([str(field) for field in fields]), self.__token, str(gardenID))
            response, content = self.__send_request(address)
        except:
            raise

    def remove_weed_on_field_in_garden(self, gardenID, fieldID):
        """Befreit ein Feld im Garten von Unkraut."""
        self._change_garden(gardenID)
        try:
            response, content = self.__send_request('save/abriss.php?tile={}'.format(fieldID), 'POST')
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_success(content)
            return jContent['success']
        except:
            raise

    # aqua garden
    # TODO: check if required (should be deprecated because of new garden presentation)
    def __find_empty_aqua_fields_from_json_content(self, jContent):
        emptyAquaFields = []
        for field in jContent['garden']:
            if jContent['garden'][field][0] == 0:
                emptyAquaFields.append(int(field))
        # Sortierung über ein leeres Array ändert Objekttyp zu None
        if len(emptyAquaFields) > 0:
            emptyAquaFields.sort(reverse=False)
        return emptyAquaFields

    # TODO: redo this the same way like normal gardens
    def get_plants_to_water_in_aqua_garden(self):
        """
        Ermittelt alle bepflanzten Felder im Wassergartens, die auch gegossen werden können und gibt diese zurück.
        """
        try:
            response, content = self.__send_request(
                'ajax/ajax.php?do=watergardenGetGarden&token={}'.format(self.__token))
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            return self.__find_plants_to_be_watered_from_json_content(jContent)
        except:
            raise

    def water_plant_in_aqua_garden(self, iField, sFieldsToWater):
        """Gießt alle Pflanzen im Wassergarten"""
        listFieldsToWater = sFieldsToWater.split(',')

        sFields = ''
        for i in listFieldsToWater:
            sFields += '&water[]={}'.format(i)

        try:
            address = 'ajax/ajax.php?do=watergardenCache{}&token={}'.format(sFields, self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
        except:
            raise

    def is_aqua_garden_available(self, iUserLevel):
        """
        Funktion ermittelt, ob ein Wassergarten verfügbar ist.
        Dazu muss ein Mindestlevel von 19 erreicht sein und dieser dann freigeschaltet sein.
        Die Freischaltung wird anhand der Errungenschaften im Spiel geprüft.
        """
        if not (iUserLevel < 19):
            try:
                response, content = self.__send_request('ajax/achievements.php?token={}'.format(self.__token))
                self.__check_http_ok(response)
                jContent = self.__generate_json_and_check_ok(content)
            except:
                raise
            else:
                result = re.search(r'trophy_54.png\);[^;]*(gray)[^;^class$]*class', jContent['html'])
                return result is None
        else:
            return False

    # TODO: check if required (should be deprecated because of new garden presentation)
    def get_empty_fields_aqua(self):
        try:
            address = 'ajax/ajax.php?do=watergardenGetGarden&token={}'.format(self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            emptyAquaFields = self.__find_empty_aqua_fields_from_json_content(jContent)
        except:
            raise
        else:
            return emptyAquaFields

    def harvest_aqua_garden(self):
        """Erntet alle fertigen Pflanzen im Garten."""
        try:
            address = 'ajax/ajax.php?do=watergardenHarvestAll&token={}'.format(self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
        except:
            raise

    def grow_aqua_plant(self, plant, field):
        """Baut eine Pflanze im Wassergarten an."""
        headers = self.__get_header()
        server = self.__get_url()
        adresse = '{}ajax/ajax.php?do=watergardenCache&plant[{}]={}&token={}'.format(server, plant, field, self.__token)
        try:
            response, content = self.__webclient.request(adresse, 'GET', headers=headers)
        except:
            raise

    def remove_weed_on_field_in_aqua_garden(self, gardenID, fieldID):
        """Befreit ein Feld im Garten von Unkraut."""
        self._change_garden(gardenID)
        try:
            response, content = self.__send_request('save/abriss.php?tile={}'.format(fieldID), 'POST')
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_success(content)
            return jContent['success']
        except:
            raise

    # bee farm
    def is_honey_farm_available(self, iUserLevel):
        if not (iUserLevel < 10):
            try:
                response, content = self.__send_request('ajax/ajax.php?do=citymap_init&token={}'.format(self.__token))
                self.__check_http_ok(response)
                jContent = self.__generate_json_and_check_ok(content)
                return jContent['data']['location']['bees']['bought'] == 1
            except:
                raise
        else:
            return False

    # TODO: merge __get_available_hives and __get_hive_type
    def __get_available_hives(self, jContent):
        """Sucht im JSON Content nach verfügbaren Bienenstöcken und gibt diese zurück."""
        availableHives = []

        for hive in jContent['data']['data']['hives']:
            if "blocked" not in jContent['data']['data']['hives'][hive]:
                availableHives.append(int(hive))

        # Sortierung über ein leeres Array ändert Objekttyp zu None
        if len(availableHives) > 0:
            availableHives.sort(reverse=False)

        return availableHives

    # TODO: merge __get_available_hives and __get_hive_type
    def __get_hive_type(self, jContent):
        """Sucht im JSON Content nach dem Typ der Bienenstöcke und gibt diese zurück."""
        hiveType = []

        for hive in jContent['data']['data']['hives']:
            if "blocked" not in jContent['data']['data']['hives'][hive]:
                hiveType.append(int(hive))

        # Sortierung über ein leeres Array ändert Objekttyp zu None
        if len(hiveType) > 0:
            hiveType.sort(reverse=False)

        return hiveType

    def get_honey_farm_infos(self):
        """Funktion ermittelt, alle wichtigen Informationen der Bienengarten und gibt diese aus."""
        try:
            response, content = self.__send_request('ajax/ajax.php?do=bees_init&token={}'.format(self.__token))
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            honeyQuestNr = jContent['questnr']
            honeyQuest = self.__get_honey_quest(jContent)
            hives = self.__get_available_hives(jContent)
            hivetype = self.__get_hive_type(jContent)
            return honeyQuestNr, honeyQuest, hives, hivetype
        except:
            raise

    def change_hives_type_quest(self, hive, Questanforderung):
        """Ändert den Typ vom Bienenstock auf die Questanforderung."""
        try:
            address = 'ajax/ajax.php?do=bees_changehiveproduct&id={}' \
                      '&pid={}&token={}'.format(str(hive), str(Questanforderung), self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
        except:
            pass

    def harvest_bees(self):
        """Erntet den vollen Honigtopf"""
        try:
            response, content = self.__send_request('ajax/ajax.php?do=bees_fill&token={}'.format(self.__token))
            self.__check_http_ok(response)
        except:
            raise

    def send_bees(self, hive):
        """Sendet die Bienen für 2 Stunden"""
        # TODO: Check if bee is sent, sometimes 1 hives got skipped
        try:
            address = 'ajax/ajax.php?do=bees_startflight&id={}&tour=1&token={}'.format(str(hive), self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
        except:
            pass

    # bonsai farm
    def is_bonsai_farm_available(self, iUserLevel):
        if iUserLevel < 10:
            return False
        try:
            response, content = self.__send_request('ajax/ajax.php?do=citymap_init&token={}'.format(self.__token))
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            location = jContent['data']['location']
            bought_bonsai = jContent['data']['location']['bonsai']['bought']
            return 'bonsai' in location and bought_bonsai == 1
        except:
            raise

    def __get_available_bonsai_slots(self, jContent):
        """Sucht im JSON Content nach verfügbaren bonsai und gibt diese zurück."""
        availableTreeSlots = []

        for tree in jContent['data']['data']['slots']:
            if "block" not in jContent['data']['data']['slots'][tree]:
                availableTreeSlots.append(int(tree))

        # Sortierung über ein leeres Array ändert Objekttyp zu None
        if len(availableTreeSlots) > 0:
            availableTreeSlots.sort(reverse=False)

        return availableTreeSlots

    def get_bonsai_farm_infos(self):
        """Funktion ermittelt, alle wichtigen Informationen der Bonsai garten und gibt diese aus."""
        adresse = 'ajax/ajax.php?do=bonsai_init&token={}'.format(self.__token)
        try:
            response, content = self.__send_request(f'{adresse}')
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            bonsaiquestnr = jContent['questnr']
            bonsaiquest = self.__get_bonsai_quest(jContent)
            bonsaislots = self.__get_available_bonsai_slots(jContent)
            return bonsaiquestnr, bonsaiquest, bonsaislots, jContent
        except:
            raise

    def cut_bonsai(self, tree, sissor):
        """Schneidet den Ast vom Bonsai"""
        try:
            address = 'ajax/ajax.php?do=bonsai_branch_click&slot={}' \
                      '&scissor={}&cache=%5B1%5D&token={}'.format(str(tree), str(sissor), self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
        except:
            pass

    ###########
    # Trading #
    ###########
    # wimps
    def __find_wimps_data_from_json_content(self, jContent):
        """Returns list of growing plants from JSON content"""
        wimpsData = {}
        for wimp in jContent['wimps']:
            product_data = {}
            wimp_id = wimp['sheet']['id']
            cash = wimp['sheet']['sum']
            for product in wimp['sheet']['products']:
                product_data[str(product['pid'])] = int(product['amount'])
            wimpsData[wimp_id] = [cash, product_data]
        return wimpsData

    def get_wimps_data(self, gardenID):
        """Get wimps data including wimp_id and list of products with amount"""
        try:
            self._change_garden(gardenID)

            response, content = self.__send_request('ajax/verkaufajax.php?do=getAreaData&token={}'.format(self.__token))
            self.__check_http_ok(response)

            jContent = self.__generate_json_and_check_ok(content)
            return self.__find_wimps_data_from_json_content(jContent)
        except:
            raise

    def sell_wimp_products(self, wimp_id):
        """
        Sell products to wimp with a given id
        @param wimp_id: str
        @return: dict of new balance of sold products
        """
        try:
            address = 'ajax/verkaufajax.php?do=accept&id={}&token={}'.format(wimp_id, self.__token)
            response, content = self.__send_request(address, 'POST')
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            return jContent['newProductCounts']
        except:
            pass

    def decline_wimp(self, wimp_id):
        """
        Decline wimp with a given id
        @param wimp_id: str
        @return: 'decline'
        """
        try:
            address = 'ajax/verkaufajax.php?do=decline&id={}&token={}'.format(wimp_id, self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            return jContent['action']
        except:
            pass

    # Shops
    def __parse_npc_prices_from_html(self, html_data):
        """Parsen aller NPC Preise aus dem HTML Skript der Spielehilfe."""
        #ElementTree benötigt eine Datei zum Parsen.
        #Mit BytesIO wird eine Datei im Speicher angelegt, nicht auf der Festplatte.
        my_parser = etree.HTMLParser(recover=True)
        html_tree = etree.fromstring(str(html_data), parser=my_parser)

        table = html_tree.find('./body/div[@id="content"]/table')
        
        dictResult = {}
        
        for row in table.iter('tr'):
            
            produktname = row[0].text
            npc_preis = row[1].text
            
            #Bei der Tabellenüberschrift ist der Text None
            if produktname != None and npc_preis != None:
                # NPC-Preis aufbereiten
                npc_preis = str(npc_preis)
                npc_preis = npc_preis[0:len(npc_preis) - 3]
                npc_preis = npc_preis.replace('.', '')
                npc_preis = npc_preis.replace(',', '.')
                npc_preis = npc_preis.strip()
                if len(npc_preis) == 0:
                    npc_preis = None
                else:
                    npc_preis = float(npc_preis)
                    
                dictResult[produktname] = npc_preis
                
        return dictResult

    def get_npc_prices(self):
        """Ermittelt aus der Wurzelimperium-Hilfe die NPC Preise aller Produkte."""
        response, content = self.__send_request('hilfe.php?item=2')
        self.__check_http_ok(response)
        content = content.decode('UTF-8').replace('Gärten & Regale', 'Gärten und Regale')
        dictNPCPrices = self.__parse_npc_prices_from_html(content)
        return dictNPCPrices

    def get_offers_from_product(self, prod_id):
        """Gibt eine Liste mit allen Angeboten eines Produkts zurück."""
        nextPage = True
        iPage = 1
        listOffers = []
        while nextPage:
            nextPage = False

            try:
                address = 'stadt/markt.php?order=p&v={}&filter=1&page={}'.format(str(prod_id), str(iPage))
                response, content = self.__send_request(address)
                self.__check_http_ok(response)
            except:
                pass  # TODO: exception definieren
            else:
                html_file = io.BytesIO(content)
                html_tree = html.parse(html_file)
                root = html_tree.getroot()
                table = root.findall('./body/div/table/*')

                if table[1][0].text == 'Keine Angebote':
                    pass
                else:
                    # range von 1 bis länge-1, da erste Zeile Überschriften sind und die letzte Weiter/Zurück.
                    # Falls es mehrere seiten gibt.
                    for i in range(1, len(table) - 1):
                        anzahl = table[i][0].text
                        anzahl = anzahl.encode('utf-8')
                        anzahl = anzahl.replace('.', '')

                        preis = table[i][3].text
                        preis = preis.encode('utf-8')
                        preis = preis.replace('\xc2\xa0wT', '')
                        preis = preis.replace('.', '')
                        preis = preis.replace(',', '.')
                        # produkt = table[i][1][0].text
                        # verkaeufer = table[i][2][0].text

                        listOffers.append([int(anzahl), float(preis)])

                    for element in table[len(table) - 1][0]:
                        if 'weiter' in element.text:
                            nextPage = True
                            iPage = iPage + 1

        return listOffers

    def buy_from_shop(self, shop: int, productId: int, amount: int = 1):
        parameter = urlencode({'s': shop,
                               'page': 1,
                               'change_page_only': 0,
                               'produkt[0]': productId,
                               'anzahl[0]': amount
                               })
        try:
            header = {'Content-Type': 'application/x-www-form-urlencoded'}
            response, content = self.__send_request('stadt/shop.php?s={}'.format(shop), 'POST', parameter, header)
            self.__check_http_ok(response)
        except:
            raise

    def buy_from_aqua_shop(self, productId: int, amount: int = 1):
        adresse = 'ajax/ajax.php?products={}:{}&do=shopBuyProducts&type=aqua&token={}'\
                  .format(productId, amount, self.__token)

        try:
            response, content = self.__send_request(f'{adresse}')
            self.__check_http_ok(response)
        except:
            return ''

    ######################
    # Quests and Bonuses #
    ######################
    # bonuses
    def collect_daily_login_bonus(self, day):
        """
        @param day: string (day of daily bonus)
        """
        try:
            address = 'ajax/ajax.php?do=dailyloginbonus_getreward&day={}&token={}'.format(day, self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
            return self.__generate_json_and_check_ok(content)
        except:
            pass

    def get_big_quest_data(self):
        """Returns Data from Yearly Series of Quests"""
        try:
            address = 'ajax/ajax.php?do=bigquest_init&id=3&token={}'.format(self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            return jContent['data']
        except:
            pass

    def init_infinity_quest(self):
        headers = self.__get_header()
        server = self.__get_url()
        adresse = '{}ajax/ajax.php?do=infinite_quest_get&token={}'.format(server, self.__token)
        try:
            response, content = self.__webclient.request(adresse, 'GET', headers=headers)
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            return jContent
        except:
            pass

    def send_infinity_quest(self, questnr, product, amount):
        try:
            address = 'ajax/ajax.php?do=infinite_quest_entry&pid={}' \
                      '&amount={}&questnr={}&token={}'.format(product, amount, questnr, self.__token)
            response, content = self.__send_request(address)
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            return jContent
        except:
            pass

    def __get_honey_quest(self, jContent):
        """Sucht im JSON Content nach verfügbaren Bienenquesten und gibt diese zurück."""
        honeyQuest = {}
        i = 1
        for course in jContent['questData']['products']:
            new = {i: {'pid': course['pid'], 'type': course['name']}}
            honeyQuest.update(new)
            i = i + 1
        return honeyQuest

    def __get_bonsai_quest(self, jContent):
        """Sucht im JSON Content nach verfügbaren bonsaiquesten und gibt diese zurück."""
        bonsaiQuest = {}
        i = 1
        for course in jContent['questData']['products']:
            new = {i: {'pid': course['pid'], 'type': course['name']}}
            bonsaiQuest.update(new)
            i = i + 1
        return bonsaiQuest

    #######################
    # Messaging and Notes #
    #######################
    def create_new_message_and_return_result(self):
        """Erstellt eine neue Nachricht und gibt deren ID zurück, die für das Senden benötigt wird."""
        try:
            response, content = self.__send_request('nachrichten/new.php')
            self.__check_http_ok(response)
            return content
        except:
            raise

    def send_message_and_return_result(self, msg_id, msg_to, msg_subject, msg_body):
        """Verschickt eine Nachricht mit den übergebenen Parametern."""
        parameter = urlencode({'hpc': msg_id,
                               'msg_to': msg_to,
                               'msg_subject': msg_subject,
                               'msg_body': msg_body,
                               'msg_send': 'senden'}) 
        try:
            response, content = self.__send_request('nachrichten/new.php', 'POST', parameter)
            self.__check_http_ok(response)
            return content
        except:
            raise

    def get_note(self):
        """Get the users note"""
        try:
            response, content = self.__send_request('notiz.php', 'POST')
            self.__check_http_ok(response)
            content = content.decode('UTF-8')
            my_parser = etree.HTMLParser(recover=True)
            html_tree = etree.fromstring(content, parser=my_parser)

            note = html_tree.find('./body/form/div/textarea[@id="notiztext"]')
            noteText = note.text
            if noteText is None:
                return ''
            return noteText.strip()
        except:
            raise

    ########################
    # Products and Storage #
    ########################
    def get_all_product_informations(self):
        """Sammelt alle Produktinformationen und gibt diese zur Weiterverarbeitung zurück."""
        try:
            response, content = self.__send_request('main.php?page=garden')
            content = content.decode('UTF-8')
            self.__check_http_ok(response)
            reToken = re.search(r'ajax\.setToken\(\"(.*)\"\);', content)
            self.__token = reToken.group(1) #TODO: except, wenn token nicht aktualisiert werden kann
            reProducts = re.search(r'data_products = ({.*}});var', content)
            return reProducts.group(1)
        except:
            raise

    def get_inventory(self):
        """Ermittelt den Lagerbestand und gibt diesen zurück."""
        try:
            address = 'ajax/updatelager.php?all=1&sort=1&type=honey&token={}'.format(self.__token)
            response, content = self.__send_request(address, 'POST')
            self.__check_http_ok(response)
            jContent = self.__generate_json_and_check_ok(content)
            return jContent['produkte']
        except:
            pass

    def get_all_tradeable_products_from_overview(self):
        """Gibt eine Liste zurück, welche Produkte handelbar sind."""
        try:
            response, content = self.__send_request('stadt/markt.php?show=overview')
            self.__check_http_ok(response)
            tradeableProducts = re.findall(r'markt\.php\?order=p&v=([0-9]{1,3})&filter=1', content)
        except:
            pass  # TODO: exception definieren
        else:
            for i in range(0, len(tradeableProducts)):
                tradeableProducts[i] = int(tradeableProducts[i])
                
            return tradeableProducts


class HTTPStateError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class JSONError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class HTTPRequestError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class YAMLError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


http_connection = HTTPConnection()
