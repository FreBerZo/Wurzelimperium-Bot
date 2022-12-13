from wurzelbot.Spieler import spieler
from wurzelbot.HTTPCommunication import http_connection


class Collector:
    def collect_daily_login_bonus(self):
        bonuses = spieler.get_daily_login_bonus()
        for day, bonus in bonuses['data']['rewards'].items():
            if 'done' not in bonus:
                if any(price in bonus for price in ('money', 'products')):
                    http_connection.getDailyLoginBonus(day)


collector = Collector()
