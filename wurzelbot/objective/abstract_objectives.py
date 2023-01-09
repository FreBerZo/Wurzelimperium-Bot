import abc
import logging
import inspect


class Objective(metaclass=abc.ABCMeta):
    def __init__(self, priority):
        self.priority = priority
        self.sub_objectives = []

    def __lt__(self, other):
        return self.priority < other.priority

    def get_reservations(self):
        return True

    @abc.abstractmethod
    def is_reached(self):
        pass

    def get_finish_reservations(self):
        return True

    def finish(self):
        pass

    def get_work_reservations(self):
        return True

    def work(self):
        pass

    # TODO: IDEA: sub objectives can be created at any point and will be worked before super objective can work
    # TODO: IDEA: differentiate between prerequisite sub objective and parallel executed sub objectives
    def work_if_possible(self):
        logging.debug(f"running {inspect.getmro(self.__class__)[1].__name__}: {self}")
        # if there are sub objectives, they need to be reached first before this objective can continue
        if len(self.sub_objectives) > 0:
            for sub_objective in self.sub_objectives:
                if sub_objective.work_if_possible():
                    self.sub_objectives.remove(sub_objective)

            if len(self.sub_objectives) > 0:
                return False

        # reservations are only done for the work of this objective. NOT for sub objective
        if not self.get_reservations():
            return False

        # reservations are guaranteed for work and finish
        if self.is_reached():
            if self.get_finish_reservations():
                return self.finish()

        if not self.get_work_reservations():
            return False
        self.work()

        if self.is_reached():
            if self.get_finish_reservations():
                return self.finish()


class SubObjective(Objective, metaclass=abc.ABCMeta):
    pass


class MainObjective(Objective, metaclass=abc.ABCMeta):
    pass
