from .abstract_objectives import MainObjective
from .sub_objectives import FarmMoney


class FarmMoneyMain(MainObjective):
    """
    A test MainObjective that endlessly farms money.
    """
    
    def __init__(self):
        super().__init__(priority=1)
        # 10000 wT is just a test, maybe change this
        self.sub_objectives.append(FarmMoney(self.priority, 10000))

    def is_reached(self):
        return False
    
    def get_reservations(self):
        # the main objective doesn't need any reservations because all the work is done by the sub objective
        return True
    
    def finish(self):
        return True
    
    def work(self):
        pass
