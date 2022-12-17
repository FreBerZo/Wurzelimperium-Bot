from wurzelbot.Spieler import spieler
from wurzelbot.HTTPCommunication import http_connection
import logging


class Collector:
    def collect_daily_login_bonus(self):
        logging.info("Boni werden gesammelt.")
        bonuses = spieler.daily_login_bonus
        for day, bonus in bonuses['data']['rewards'].items():
            if 'done' not in bonus:
                if any(price in bonus for price in ('money', 'products')):
                    http_connection.collect_daily_login_bonus(day)


collector = Collector()
