import datetime
import logging

from wurzelbot.communication.http_communication import HTTPConnection
from wurzelbot.gardens.gardens import GardenManager, WeedCrop
from wurzelbot.utils.singelton_type import SingletonType
from .main_objectives import FarmMoneyMain, RemoveWeed, BigQuest


# TODO: IDEA: split into reservation phase and working phase
#  reservation phase only requests reservation
#  after reservation phase the actual resource distribution is determined
#  this is difficult because reservation amount depends on each other
#  (e.g. if no plants could be reserved tiles are not required)


class ObjectiveManager(metaclass=SingletonType):
    def __init__(self):
        self.objectives = []

    def create_objectives(self):
        logging.debug('creating objectives...')
        if self.get_objective_of_class(FarmMoneyMain) is None:
            self.objectives.append(FarmMoneyMain(10))

        weed_crops = sorted(GardenManager().get_crops_flat_from_class(WeedCrop), key=lambda crop: crop.remove_cost)
        if self.get_objective_of_class(RemoveWeed) is None and len(weed_crops) > 0:
            self.objectives.append(RemoveWeed(1, weed_crops[0]))

        garden_info = HTTPConnection().get_garden_info()
        if not garden_info == 0:
            pass

        # big quest (monthly limited quest) starts with level 1?
        year_id = datetime.datetime.now().year - 2019
        big_quest_data = HTTPConnection().get_big_quest_data(year_id)
        current_quest_id = int(big_quest_data['current'])
        current_quest_data = big_quest_data['data']['quests'][str(current_quest_id)]
        if not current_quest_data.get('done'):
            needed_products = current_quest_data['need']
            sent_products = current_quest_data.get('have')
            if sent_products is not None:
                for product_id, quantity in needed_products.items():
                    if str(product_id) in sent_products.keys():
                        needed_products[str(product_id)] -= sent_products[str(product_id)]
            self.objectives.append(BigQuest(2, year_id, current_quest_id, needed_products))

        # city quest starts with level ?
        # new city quest 48 hours after finishing the previous
        # endless quest starts with level 22

    def get_objective_of_class(self, cls):
        for objective in self.objectives:
            if isinstance(objective, cls):
                return objective
        return None

    def run_objectives(self):
        objective_finished = False
        for objective in sorted(self.objectives):
            if objective.work_if_possible():
                self.objectives.remove(objective)
                objective_finished = True
        return objective_finished
