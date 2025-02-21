from .reservation import Resource, ReservationManager


class Reservator:
    def __init__(self, objective, resource, quantity, plant=None):
        self.objective = objective
        self.resource = resource
        self.quantity = quantity
        if resource == Resource.PLANT and plant is None:
            raise ValueError("plant attribute is None")
        self.plant = plant

        existing_reservation = ReservationManager().get_reservation(self.objective, self.resource, self.plant)
        self.reservation_was_overridden = False
        if existing_reservation is not None:
            self.reservation_was_overridden = True
            self.prev_quantity = existing_reservation.quantity

    def __enter__(self):
        reserved_amount = ReservationManager().reserve(self.objective, self.resource, self.quantity, self.plant)
        return reserved_amount

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.reservation_was_overridden:
            ReservationManager().reserve(self.objective, self.resource, self.prev_quantity, self.plant)
        else:
            ReservationManager().free_reservation(self.objective, self.resource, self.plant)
