from wurzelbot.communication.http_communication import HTTPConnection
from wurzelbot.gardens.gardener import Gardener
from wurzelbot.product.product_data import ProductData
from wurzelbot.reservation.reservation import ReservationManager, Resource
from .abstract_objectives import MainObjective
from .sub_objectives import FarmMoney, FarmPlant


class FarmMoneyMain(MainObjective):
    """
    A test MainObjective that endlessly farms money.
    """

    def __init__(self, priority):
        super().__init__(priority)
        self.sub_objectives.append(FarmMoney(self.priority, -1))

    def __str__(self):
        return f"{self.__class__.__name__}(priority={self.priority})"

    def is_reached(self):
        return True


class RemoveWeed(MainObjective):
    def __init__(self, priority, crop):
        super().__init__(priority)

        self.crop = crop
        self.usable_money_quantity = 0
        self.sub_objectives.append(FarmMoney(self.priority, self.crop.remove_cost))

    def __str__(self):
        return f"{self.__class__.__name__}(priority={self.priority}, " \
               f"crop=({self.crop.remove_cost}, {self.crop.tiles[0].tile_id}))"

    def is_reached(self):
        return True

    def get_finish_reservations(self):
        self.usable_money_quantity = ReservationManager().reserve(self, Resource.MONEY, self.crop.remove_cost)
        return self.usable_money_quantity >= self.crop.remove_cost

    def finish(self):
        Gardener().remove_crop(self.crop)
        return True


class BigQuest(MainObjective):
    def __init__(self, priority, year_id, quest_id, needed_products):
        super().__init__(priority)

        self.year_id = year_id
        self.quest_id = quest_id
        self.needed_products = needed_products

        for product_id, quantity in self.needed_products.items():
            product = ProductData().get_product_by_id(int(product_id))
            self.sub_objectives.append(FarmPlant(self.priority, product, quantity))
            ReservationManager().reserve(self, Resource.PLANT, quantity, product)

    def __str__(self):
        return f"{self.__class__.__name__}(priority={self.priority}, year={self.year_id + 2019}, month={self.quest_id})"

    def is_reached(self):
        # the objective is always reached of the sub objectives finished
        return True

    def get_finish_reservations(self):
        for product_id, quantity in self.needed_products.items():
            product = ProductData().get_product_by_id(int(product_id))
            reserved_quantity = ReservationManager().reserve(self, Resource.PLANT, quantity, product)
            if reserved_quantity < quantity:
                return False
        return True

    def finish(self):

        for product_id, quantity in self.needed_products.items():
            product = ProductData().get_product_by_id(int(product_id))
            HTTPConnection().send_big_quest_data(self.year_id, self.quest_id, product, quantity)
            ReservationManager().free_reservation(self, Resource.PLANT, product)
        return True
