from .abstract_objectives import MainObjective
from .sub_objectives import FarmMoney

from wurzelbot.reservation import reservation_manager, Resource
from wurzelbot.gardener import gardener


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
        self.usable_money_quantity = self.usable_money_quantity = reservation_manager.reserve(self, Resource.MONEY, self.crop.remove_cost)
        return self.usable_money_quantity >= self.crop.remove_cost

    def finish(self):
        gardener.remove_crop(self.crop)
        return True
