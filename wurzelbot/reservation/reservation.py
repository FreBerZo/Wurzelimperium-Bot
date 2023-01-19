from enum import Enum

from wurzelbot.account_data import account_data
from wurzelbot.gardens.gardener import gardener
from wurzelbot.gardens.gardens import garden_manager
from wurzelbot.product.storage import storage
from wurzelbot.trading.market import market


class Resource(Enum):
    TILE = 't'
    PLANT = 'p'
    MONEY = 'm'


class Reservation:
    def __init__(self, objective, resource, quantity, plant=None):
        self.resource = resource
        if resource == Resource.PLANT:
            self.plant = plant
        self.objective = objective
        self.quantity = quantity

    def is_resource(self, resource):
        return self.resource == resource

    def is_reserved_by(self, objective):
        return self.objective == objective


# TODO: IDEA: add difference between requested quantity and received quantity
# TODO: IDEA: add difference between shared reservation and normal reservation

class ReservationManager:
    def __init__(self):
        self.reservations = {
            Resource.PLANT.value: [],
            Resource.MONEY.value: [],
            Resource.TILE.value: [],
        }

    def reserve(self, objective, resource, quantity, plant=None):
        existing_reservation = self.get_reservation(objective, resource, plant)
        if existing_reservation is not None:
            existing_reservation.quantity = quantity
        else:
            if resource == Resource.PLANT and plant is None:
                raise ValueError("plant attribute is None")
            self.reservations.get(resource.value).append(Reservation(objective, resource, quantity, plant))

        return self.get_reservation_quantity(objective, resource, plant)

    def get_reservation(self, objective, resource, plant=None):
        for reservation in self.get_reservations(resource, plant):
            if reservation.objective == objective:
                return reservation
        return None

    def get_reservations(self, resource, plant=None):
        if resource == Resource.PLANT:
            if plant is None:
                raise ValueError("plant attribute is None")
            return [reservation for reservation in self.reservations.get(resource.value) if reservation.plant == plant]
        return self.reservations.get(resource.value)

    def get_reservation_quantity(self, objective, resource, plant=None):
        existing_reservation = self.get_reservation(objective, resource, plant)
        if existing_reservation is None:
            return 0
        already_reserved_amount = 0
        for reservation in self.get_reservations(resource, plant):
            if reservation.objective.priority < existing_reservation.objective.priority:
                if reservation.quantity == -1:
                    return 0
                already_reserved_amount += reservation.quantity

        if resource == Resource.PLANT:
            theoretical_available_quantity = gardener.get_potential_quantity_of(plant)
            actual_available_quantity = storage.get_stock_from_product(plant)
        elif resource == Resource.TILE:
            theoretical_available_quantity = garden_manager.get_num_of_plantable_tiles()
            actual_available_quantity = len(garden_manager.get_empty_tiles())
        else:
            theoretical_available_quantity = account_data.money - market.min_money()
            actual_available_quantity = theoretical_available_quantity

        requested_quantity = existing_reservation.quantity
        unreserved_quantity = theoretical_available_quantity - already_reserved_amount

        limits = [actual_available_quantity, unreserved_quantity]
        if requested_quantity != -1:
            limits.append(requested_quantity)

        min_limit = min(limits)
        return min_limit if min_limit >= 0 else 0

    def free_reservation(self, objective, resource, plant=None):
        existing_reservation = self.get_reservation(objective, resource, plant)
        if existing_reservation is None:
            return

        self.reservations.get(resource.value).remove(existing_reservation)


reservation_manager = ReservationManager()
