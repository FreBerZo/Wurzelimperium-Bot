"""
Created on 21.03.2017
@author: MrFlamez
"""
import re
from collections import namedtuple

from wurzelbot.communication.http_communication import HTTPConnection
from wurzelbot.utils.singelton_type import SingletonType

Login = namedtuple('Login', 'server user password')


class AccountData(metaclass=SingletonType):
    """
    Diese Daten-Klasse enthält alle wichtigen Informationen über den Spieler.
    """

    account_login = None
    user_name = None
    user_id = None
    money = None
    points = None
    coins = None
    level = None
    level_name = None
    time = None
    daily_login_bonus = None
    number_of_gardens = None
    guild = None
    honey_farm_available = None
    aqua_garden_available = None

    # Quests completed
    quests_completed = None
    aqua_quests_completed = None
    cactus_quests_completed = None
    echino_quests_completed = None
    bighead_quests_completed = None
    opuntia_quests_completed = None
    saguaro_quests_completed = None

    def load_garden_availability(self):
        AccountData().honey_farm_available = HTTPConnection().is_honey_farm_available(AccountData().level)

        AccountData().aqua_garden_available = HTTPConnection().is_aqua_garden_available(AccountData().level)

    def load_user_data(self):
        """
        Liest den Spielerdaten vom Server und speichert sie in der Klasse.
        """
        user_data = HTTPConnection().read_user_data_from_server()

        self.user_name = user_data['uname']
        self.money = float(user_data['bar_unformat'])
        self.points = int(user_data['points'])
        self.coins = int(user_data['coins'])
        self.level = int(user_data['levelnr'])
        self.level_name = user_data['level']
        self.time = int(user_data['time'])
        self.daily_login_bonus = user_data['dailyloginbonus']

    def load_stats(self):
        stats = HTTPConnection().get_stats()['table']
        mapping = {
            'user_id': (1, int),
            'quests_completed': (5, int),
            'aqua_quests_completed': (6, int),
            'cactus_quests_completed': (7, int),
            'echino_quests_completed': (8, int),
            'bighead_quests_completed': (9, int),
            'opuntia_quests_completed': (10, int),
            'saguaro_quests_completed': (11, int),
            'number_of_gardens': (16, int),
            'guild': (17, str),
        }

        for key, value in mapping.items():
            i, var_type = value
            stat_value = var_type(re.findall(r'<td>(.*?)</td>', stats[i])[1].replace(r'&nbsp;', ''))
            setattr(self, key, stat_value)
