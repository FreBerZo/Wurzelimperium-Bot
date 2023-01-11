import math

from wurzelbot.account_data import account_data
from wurzelbot.gardens.gardener import gardener
from wurzelbot.gardens.gardens import garden_manager
from wurzelbot.product.storage import storage
from wurzelbot.reservation.reservation import reservation_manager, Resource
from wurzelbot.reservation.reservator import Reservator
from wurzelbot.trading.trader import trader
from .abstract_objectives import SubObjective


# TODO: implement parallel sub objectives and main objectives work
# TODO: add work required function, if only waiting is required because objective is nearly reached
#  get_work_reservation can be exploited for that
# multiple sub objectives from the same class does not work until now. Because of the reach function that tracks the
# global resource reach and not reach of just the sub objective


class FarmMoney(SubObjective):
    """
    Farms certain amount of money.
    """

    def __init__(self, priority, amount, force_efficiency=True, consider_min_quantity=True):
        super().__init__(priority)
        self.amount = amount
        self.plant = None
        self.prev_plant = None
        self.fallback_plant = None
        self.prev_fallback_plant = None
        self.force_efficiency = force_efficiency
        self.consider_min_quantity = consider_min_quantity
        self.usable_plant_quantity = 0
        self.usable_prev_plant_quantity = 0
        self.usable_fallback_plant_quantity = 0
        self.usable_prev_fallback_plant_quantity = 0
        self.usable_tile_quantity = 0

    def __str__(self):
        return f"{self.__class__.__name__}(priority={self.priority}, amount={self.amount})"

    def is_reached(self):
        if self.amount == -1:
            return False
        if self.consider_min_quantity:
            return account_data.money >= self.amount + trader.min_money()
        return account_data.money >= self.amount

    def finish(self):
        if self.plant is not None:
            reservation_manager.free_reservation(self, Resource.PLANT, self.plant)
        if self.prev_plant is not None:
            reservation_manager.free_reservation(self, Resource.PLANT, self.prev_plant)
        if self.fallback_plant is not None:
            reservation_manager.free_reservation(self, Resource.PLANT, self.fallback_plant)
        if self.prev_fallback_plant is not None:
            reservation_manager.free_reservation(self, Resource.PLANT, self.prev_fallback_plant)
        reservation_manager.free_reservation(self, Resource.TILE)
        return True

    def get_work_reservations(self):
        # TODO: this should be changed if wimp serving is added
        if len(garden_manager.get_empty_tiles()) == 0:
            return False

        plants_ordered_by_profitability = trader.get_products_ordered_by_profitability()
        most_profitable_plant = plants_ordered_by_profitability[0]
        plants_ordered_by_profitability.remove(most_profitable_plant)

        if self.plant is None:
            self.plant = most_profitable_plant
        if self.plant != most_profitable_plant:
            if self.prev_plant is not None:
                reservation_manager.free_reservation(self, Resource.PLANT, self.prev_plant)
            self.prev_plant = self.plant
            self.plant = most_profitable_plant

        for product in plants_ordered_by_profitability:
            if storage.has_potential_min_quantity_for(product):
                if self.fallback_plant is None:
                    self.fallback_plant = product
                if self.fallback_plant != product:
                    if self.prev_fallback_plant is not None:
                        reservation_manager.free_reservation(self, Resource.PLANT, self.prev_fallback_plant)
                    self.prev_fallback_plant = self.fallback_plant
                    self.fallback_plant = product
                break
        if self.fallback_plant is None:
            self.fallback_plant = gardener.get_potential_plants()[-1]

        if storage.get_stock_from_product(self.plant) < len(garden_manager.get_empty_tiles()):
            # TODO: replace this with provide plant and implement money priority in provide plant
            with Reservator(self, Resource.MONEY, -1) as reserved_money_quantity:
                if reserved_money_quantity > 0:
                    reserved_money_quantity += round(trader.min_money() / 2, 2)
                    buy_quantity = len(garden_manager.get_empty_tiles()) - storage.get_stock_from_product(self.plant)
                    trader.buy_cheapest_of(self.plant, buy_quantity, reserved_money_quantity)
                else:
                    # this doesn't need reservation as it uses the min money amount to buy the most profitable plant
                    trader.buy_cheapest_of(self.plant, 4, round(account_data.money / 2, 2))

        self.usable_plant_quantity = reservation_manager.reserve(self, Resource.PLANT, -1, self.plant)
        if self.prev_plant is not None:
            self.usable_prev_plant_quantity = reservation_manager.reserve(self, Resource.PLANT, -1, self.prev_plant)
        else:
            self.usable_prev_plant_quantity = 0
        self.usable_fallback_plant_quantity = reservation_manager.reserve(self, Resource.PLANT, -1, self.fallback_plant)
        if self.prev_fallback_plant is not None:
            self.usable_prev_fallback_plant_quantity = reservation_manager.reserve(self, Resource.PLANT, -1,
                                                                                   self.prev_fallback_plant)
        else:
            self.usable_prev_fallback_plant_quantity = 0
        if self.usable_plant_quantity == 0 and self.usable_fallback_plant_quantity == 0:
            return 0
        self.usable_tile_quantity = reservation_manager.reserve(
            self, Resource.TILE, self.usable_plant_quantity + self.usable_fallback_plant_quantity)
        return self.usable_tile_quantity != 0

    def work(self):
        # first method: sell to wimps
        # (this must be first because it doesn't require money to sell so this needs to be preferred)
        # TODO: implement this

        # second method of money making: normal garden farming and selling to market

        planted_plant = gardener.plant(self.plant, min(self.usable_tile_quantity, self.usable_plant_quantity))
        self.usable_tile_quantity -= planted_plant
        planted_fallback_plant = gardener.plant(self.fallback_plant,
                                                min(self.usable_tile_quantity, self.usable_fallback_plant_quantity))

        sell_amount = self.usable_plant_quantity - planted_plant
        if sell_amount > 0:
            trader.sell(self.plant, sell_amount)
        sell_amount = self.usable_fallback_plant_quantity - planted_fallback_plant
        if sell_amount > 0:
            trader.sell(self.fallback_plant, sell_amount)
        if self.prev_plant is not None:
            trader.sell(self.prev_plant, self.usable_prev_plant_quantity)
        if self.prev_fallback_plant is not None:
            trader.sell(self.prev_fallback_plant, self.usable_prev_fallback_plant_quantity)

        if self.prev_plant is not None:
            box = storage.get_box_for_product(self.prev_plant)
            if box is None or box.min_quantity() + trader.min_sell_quantity() > box.potential_quantity():
                reservation_manager.free_reservation(self, Resource.PLANT, self.prev_plant)
                self.prev_plant = None
        if self.prev_fallback_plant is not None:
            box = storage.get_box_for_product(self.prev_fallback_plant)
            if box is None or box.min_quantity() + trader.min_sell_quantity() > box.potential_quantity():
                reservation_manager.free_reservation(self, Resource.PLANT, self.prev_fallback_plant)
                self.prev_fallback_plant = None


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

        if storage.get_potential_stock_from_product(self.plant) == 0:
            self.sub_objectives.append(ProvidePlant(self.priority, self.plant))

    def __str__(self):
        return f"{self.__class__.__name__}(priority={self.priority}, plant={self.plant}, quantity={self.quantity})"

    def reach_quantity(self):
        if self.consider_min_quantity:
            return self.plant.min_quantity() + self.quantity
        return self.quantity

    def get_reservations(self):
        self.usable_plant_quantity = reservation_manager.reserve(self, Resource.PLANT, self.reach_quantity(),
                                                                 self.plant)
        return self.usable_plant_quantity != 0

    def is_reached(self):
        return self.usable_plant_quantity >= self.reach_quantity()

    def finish(self):
        reservation_manager.free_reservation(self, Resource.PLANT, self.plant)
        reservation_manager.free_reservation(self, Resource.TILE)
        return True

    def get_work_reservations(self):
        if len(garden_manager.get_empty_tiles()) == 0:
            return False

        missing_amount = self.reach_quantity() - gardener.get_potential_quantity_of(self.plant)
        if missing_amount <= 0:
            self.usable_tile_quantity = 0
            return False
        tile_amount = math.ceil(missing_amount / (self.plant.harvest_quantity - 1))
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

    def __str__(self):
        return f"{self.__class__.__name__}(priority={self.priority}, product={self.product}, quantity={self.quantity})"

    def is_reached(self):
        return account_data.money - trader.min_money() >= self.product.price_npc * self.quantity

    def get_finish_reservations(self):
        self.usable_money_quantity = reservation_manager.reserve(self, Resource.MONEY,
                                                                 self.product.price_npc * self.quantity)
        return self.usable_money_quantity != 0

    def finish(self):
        trader.buy_cheapest_of(self.product, self.quantity, self.usable_money_quantity)
        reservation_manager.free_reservation(self, Resource.MONEY)
        return True

    def work(self):
        # work is done by sub objectives and buying the plant is done at finish therefore there is no need to work
        # also this should never be reached, because if so this objectives is in an endless loop
        raise NotImplementedError("Provide plant work function has been reached.")
