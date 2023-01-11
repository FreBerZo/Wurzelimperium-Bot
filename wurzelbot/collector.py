import logging

from wurzelbot.account_data import account_data
from wurzelbot.communication.http_communication import http_connection


class Collector:
    def collect_daily_login_bonus(self):
        logging.info("collecting bonus...")
        collected_bonus = 0
        bonuses = account_data.daily_login_bonus
        for day, bonus in bonuses['data']['rewards'].items():
            if 'done' not in bonus:
                if any(price in bonus for price in ('money', 'products')):
                    collected_bonus += 1
                    http_connection.collect_daily_login_bonus(day)

        if collected_bonus > 0:
            logging.info(f"collected {collected_bonus} bonus")
        else:
            logging.info("no bonus available")


collector = Collector()
