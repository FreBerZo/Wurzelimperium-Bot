from .abstract_objectives import MainObjective
from .sub_objectives import FarmMoney, FarmPlant

from wurzelbot.reservation import reservation_manager, Resource
from wurzelbot.gardener import gardener
from wurzelbot.Produktdaten import product_data
from wurzelbot.HTTPCommunication import http_connection


class FarmMoneyMain(MainObjective):
    """
    A test MainObjective that endlessly farms money.
    """
    
    def __init__(self, priority):
        super().__init__(priority)
        self.sub_objectives.append(FarmMoney(self.priority, -1))

    def is_reached(self):
        return True


class RemoveWeed(MainObjective):
    def __init__(self, priority, crop):
        super().__init__(priority)

        self.crop = crop
        self.usable_money_quantity = 0
        self.sub_objectives.append(FarmMoney(self.priority, self.crop.remove_cost))

    def is_reached(self):
        return True

    def get_finish_reservations(self):
        self.usable_money_quantity = reservation_manager.reserve(self, Resource.MONEY, self.crop.remove_cost)
        return self.usable_money_quantity >= self.crop.remove_cost

    def finish(self):
        gardener.remove_crop(self.crop)
        return True


class BigQuest(MainObjective):
    def __init__(self, priority, year_id, quest_id, needed_products):
        super().__init__(priority)

        self.year_id = year_id
        self.quest_id = quest_id
        self.needed_products = needed_products

        for product_id, quantity in self.needed_products.items():
            product = product_data.get_product_by_id(int(product_id))
            self.sub_objectives.append(FarmPlant(self.priority, product, quantity))
            reservation_manager.reserve(self, Resource.PLANT, quantity, product)

    def is_reached(self):
        # the objective is always reached of the sub objectives finished
        return True

    def get_finish_reservations(self):
        for product_id, quantity in self.needed_products.items():
            product = product_data.get_product_by_id(int(product_id))
            reserved_quantity = reservation_manager.reserve(self, Resource.PLANT, quantity, product)
            if reserved_quantity < quantity:
                return False
        return True

    def finish(self):

        for product_id, quantity in self.needed_products.items():
            product = product_data.get_product_by_id(int(product_id))
            http_connection.send_big_quest_data(self.year_id, self.quest_id, product, quantity)
            reservation_manager.free_reservation(self, Resource.PLANT, product)
        return True
