import logging

from wurzelbot.account_data import AccountData
from wurzelbot.communication.http_communication import HTTPConnection


class Collector:
    @staticmethod
    def collect_daily_login_bonus():
        logging.info("collecting bonus...")
        collected_bonus = 0
        bonuses = AccountData().daily_login_bonus
        for day, bonus in bonuses['data']['rewards'].items():
            if 'done' not in bonus:
                if any(price in bonus for price in ('money', 'products')):
                    collected_bonus += 1
                    HTTPConnection().collect_daily_login_bonus(day)

        if collected_bonus > 0:
            logging.info(f"collected {collected_bonus} bonus")
        else:
            logging.info("no bonus available")
