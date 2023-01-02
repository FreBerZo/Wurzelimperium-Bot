from .main_objectives import FarmMoneyMain

# TODO: IDEA: split into reservation phase and working phase
#  reservation phase only requests reservation
#  after reservation phase the actual resource distribution is determined
#  this is difficult because reservation amount depends on each other
#  (e.g. if no plants could be reserved tiles are not required)


class ObjectiveManager:
    def __init__(self):
        self.objectives = []

    def create_objectives(self):
        self.objectives.append(FarmMoneyMain())

    def run_objectives(self):
        objective_finished = False
        for objective in sorted(self.objectives):
            if objective.work_if_possible():
                objective_finished = True
        return objective_finished


objective_manager = ObjectiveManager()
