import math

from wurzelbot.Spieler import spieler
from wurzelbot.Marktplatz import trader
from wurzelbot.Lager import storage
from wurzelbot.Garten import garden_manager
from wurzelbot.gardener import gardener
from wurzelbot.reservation import reservation_manager, Reservator, Resource

from .abstract_objectives import SubObjective


# TODO: add work required function, if only waiting is required because objective is nearly reached - get_work_reservation can be exploited for that
# multiple sub objectives from the same class does not work until now. Because of the reach function that tracks the
# global resource reach and not reach of just the sub objective
# TODO: what about FarmMoney singleton? -> actually good idea

class FarmMoney(SubObjective):
    """
    Farms certain amount of money.
    """
    def __init__(self, priority, amount, force_efficiency=True, consider_min_quantity=True):
        super().__init__(priority)
        self.amount = amount
        self.normal_farm_plant = None
        self.force_efficiency = force_efficiency
        self.consider_min_quantity = consider_min_quantity
        self.usable_plant_quantity = 0
        self.usable_tile_quantity = 0
        # TODO: this should better go to reservation
        for product in trader.get_products_ordered_by_profitability():
            if self.force_efficiency or storage.has_potential_min_quantity_for(product):
                self.normal_farm_plant = product
                break

        if self.normal_farm_plant is None:
            self.normal_farm_plant = gardener.get_potential_plants()[-1]

        if storage.get_stock_from_product(self.normal_farm_plant) < len(garden_manager.get_empty_tiles()):
            with Reservator(self, Resource.MONEY, -1) as reserved_money_quantity:
                buy_quantity = len(garden_manager.get_empty_tiles()) - storage.get_stock_from_product(self.normal_farm_plant)
                trader.buy_cheapest_of(self.normal_farm_plant, buy_quantity, reserved_money_quantity)

            if gardener.get_potential_quantity_of(self.normal_farm_plant) <= 0:
                self.sub_objectives.append(ProvidePlant(self.priority, self.normal_farm_plant))

    def get_reservations(self):
        self.usable_plant_quantity = reservation_manager.reserve(self, Resource.PLANT, -1, self.normal_farm_plant)
        return self.usable_plant_quantity != 0

    def is_reached(self):
        if self.consider_min_quantity:
            return spieler.money >= self.amount + trader.min_money()
        return spieler.money >= self.amount

    def finish(self):
        reservation_manager.free_reservation(self, Resource.PLANT, self.normal_farm_plant)
        reservation_manager.free_reservation(self, Resource.TILE)
        return True

    def get_work_reservations(self):
        self.usable_tile_quantity = reservation_manager.reserve(self, Resource.TILE, self.usable_plant_quantity)
        return self.usable_tile_quantity != 0

    def work(self):
        # first method: sell to wimps
        # (this must be first because it doesn't require money to sell so this needs to be preferred)
        # TODO: implement this

        # second method of money making: normal garden farming and selling to market
        gardener.plant(self.normal_farm_plant, self.usable_tile_quantity)
        # TODO: dont sell max, but only available of reserved amount
        trader.sell_max_of(self.normal_farm_plant)


class FarmPlant(SubObjective):
    """
    Farms a certain amount for a plant. Initial stock of plant is irrelevant.
    """
    def __init__(self, priority, product, quantity, consider_min_quantity=True):
        super().__init__(priority)
        self.plant = product
        self.quantity = quantity
        self.consider_min_quantity = consider_min_quantity
        self.usable_plant_quantity = 0
        self.usable_tile_quantity = 0
        self.missing_amount = 0

        if storage.get_stock_from_product(self.plant) == 0:
            self.sub_objectives.append(ProvidePlant(self.priority, self.plant))

    def reach_quantity(self):
        if self.consider_min_quantity:
            return storage.get_box_for_product(self.plant).min_quantity() + self.quantity
        return self.quantity

    def get_reservations(self):
        self.usable_plant_quantity = reservation_manager.reserve(self, Resource.PLANT, self.reach_quantity(), self.plant)
        return self.usable_plant_quantity != 0

    def is_reached(self):
        return gardener.get_potential_quantity_of(self.plant) >= self.reach_quantity()

    def finish(self):
        reservation_manager.free_reservation(self, Resource.PLANT, self.plant)
        reservation_manager.free_reservation(self, Resource.TILE)
        return True

    def get_work_reservations(self):
        # TODO: put this part in another method
        missing_amount = self.reach_quantity() - gardener.get_potential_quantity_of(self.plant)
        if missing_amount <= 0:
            self.usable_tile_quantity = 0
            return False
        tile_amount = math.ceil(missing_amount / self.plant.harvest_quantity)
        if self.usable_plant_quantity < tile_amount:
            tile_amount = self.usable_plant_quantity
        self.usable_tile_quantity = reservation_manager.reserve(self, Resource.TILE, tile_amount)
        return self.usable_tile_quantity != 0

    def work(self):
        gardener.plant(self.plant, self.usable_tile_quantity)


class ProvidePlant(SubObjective):
    """
    Provides a certain amount of a plant if there is NONE or not enough to farm available. e.g. less than 4
    """
    def __init__(self, priority, product, quantity=4):
        super().__init__(priority)
        self.product = product
        self.quantity = quantity
        self.usable_money_quantity = 0

        self.sub_objectives.append(FarmMoney(self.priority, self.product.price_npc * self.quantity, False))

    def is_reached(self):
        return spieler.money - trader.min_money >= self.product.price_npc * self.quantity

    def get_finish_reservations(self):
        self.usable_money_quantity = reservation_manager.reserve(self, Resource.MONEY,
                                                                 self.product.price_npc * self.quantity)
        return self.usable_money_quantity != 0

    def finish(self):
        trader.buy_cheapest_of(self.product, self.quantity, self.usable_money_quantity)
        reservation_manager.free_money(self)
        return True

    def work(self):
        # work is done by sub objective and buying the plant is done at finish therefore there is no need to work
        # also this should never be reached, because if so this objective is in an endless loop
        raise NotImplementedError("Provide plant work function has been reached.")
