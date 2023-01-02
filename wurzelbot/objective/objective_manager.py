from .main_objectives import FarmMoneyMain, RemoveWeed

from wurzelbot.Garten import garden_manager, WeedCrop

# TODO: IDEA: split into reservation phase and working phase
#  reservation phase only requests reservation
#  after reservation phase the actual resource distribution is determined
#  this is difficult because reservation amount depends on each other
#  (e.g. if no plants could be reserved tiles are not required)


class ObjectiveManager:
    def __init__(self):
        self.objectives = []

    def create_objectives(self):
        if self.get_objective_of_class(FarmMoneyMain) is None:
            self.objectives.append(FarmMoneyMain(10))

        weed_crops = sorted(garden_manager.get_crops_flat_from_class(WeedCrop), key=lambda crop: crop.remove_cost)
        if self.get_objective_of_class(RemoveWeed) is None and len(weed_crops) > 0:
            self.objectives.append(RemoveWeed(1, weed_crops[0]))

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


objective_manager = ObjectiveManager()
