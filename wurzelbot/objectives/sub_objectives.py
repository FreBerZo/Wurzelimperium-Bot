import math

from wurzelbot.account_data import AccountData
from wurzelbot.gardens.garden_helper import GardenHelper
from wurzelbot.gardens.gardener import Gardener
from wurzelbot.gardens.gardens import GardenManager
from wurzelbot.product.product_helper import ProductHelper
from wurzelbot.product.storage import Storage
from wurzelbot.reservation.reservation import ReservationManager, Resource
from wurzelbot.reservation.reservator import Reservator
from wurzelbot.trading.market import Market
from wurzelbot.trading.trader import Trader
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
            return AccountData().money >= self.amount + Market().min_money()
        return AccountData().money >= self.amount

    def finish(self):
        if self.plant is not None:
            ReservationManager().free_reservation(self, Resource.PLANT, self.plant)
        if self.prev_plant is not None:
            ReservationManager().free_reservation(self, Resource.PLANT, self.prev_plant)
        if self.fallback_plant is not None:
            ReservationManager().free_reservation(self, Resource.PLANT, self.fallback_plant)
        if self.prev_fallback_plant is not None:
            ReservationManager().free_reservation(self, Resource.PLANT, self.prev_fallback_plant)
        ReservationManager().free_reservation(self, Resource.TILE)
        return True

    # TODO: find out why why this sub objective does not plant after buying
    def get_work_reservations(self):
        # TODO: this should be changed if wimp serving is added
        if len(GardenManager().get_empty_tiles()) == 0:
            return False

        plants_ordered_by_profitability = Market().get_products_ordered_by_profitability()
        most_profitable_plant = plants_ordered_by_profitability[0]
        plants_ordered_by_profitability.remove(most_profitable_plant)

        if self.plant is None:
            self.plant = most_profitable_plant
        if self.plant != most_profitable_plant:
            if self.prev_plant is not None:
                ReservationManager().free_reservation(self, Resource.PLANT, self.prev_plant)
            self.prev_plant = self.plant
            self.plant = most_profitable_plant

        for product in plants_ordered_by_profitability:
            if ProductHelper.is_potential_min_quantity(product):
                if self.fallback_plant is None:
                    self.fallback_plant = product
                if self.fallback_plant != product:
                    if self.prev_fallback_plant is not None:
                        ReservationManager().free_reservation(self, Resource.PLANT, self.prev_fallback_plant)
                    self.prev_fallback_plant = self.fallback_plant
                    self.fallback_plant = product
                break
        if self.fallback_plant is None:
            self.fallback_plant = GardenHelper.get_potential_plants()[-1]

        if Storage().get_stock_from_product(self.plant) < len(GardenManager().get_empty_tiles()):
            # TODO: replace this with provide plant and implement money priority in provide plant
            # TODO: continue here
            with Reservator(self, Resource.MONEY, -1) as reserved_money_quantity:
                if reserved_money_quantity > 0:
                    reserved_money_quantity += round(Market().min_money() / 2, 2)
                    buy_quantity = len(GardenManager().get_empty_tiles()) - Storage().get_stock_from_product(self.plant)
                    Trader.buy_cheapest_of(self.plant, buy_quantity, reserved_money_quantity)
                else:
                    # this doesn't need reservation as it uses the min money amount to buy the most profitable plant
                    Trader.buy_cheapest_of(self.plant, 4, round(AccountData().money / 2, 2))

        self.usable_plant_quantity = ReservationManager().reserve(self, Resource.PLANT, -1, self.plant)
        if self.prev_plant is not None:
            self.usable_prev_plant_quantity = ReservationManager().reserve(self, Resource.PLANT, -1, self.prev_plant)
        else:
            self.usable_prev_plant_quantity = 0
        self.usable_fallback_plant_quantity = ReservationManager().reserve(self, Resource.PLANT, -1,
                                                                           self.fallback_plant)
        if self.prev_fallback_plant is not None:
            self.usable_prev_fallback_plant_quantity = ReservationManager().reserve(self, Resource.PLANT, -1,
                                                                                    self.prev_fallback_plant)
        else:
            self.usable_prev_fallback_plant_quantity = 0
        if self.usable_plant_quantity == 0 and self.usable_fallback_plant_quantity == 0:
            return 0
        self.usable_tile_quantity = ReservationManager().reserve(
            self, Resource.TILE, self.usable_plant_quantity + self.usable_fallback_plant_quantity)
        return self.usable_tile_quantity != 0

    def work(self):
        # first method: sell to wimps
        # (this must be first because it doesn't require money to sell so this needs to be preferred)
        # TODO: continue here
        # TODO: implement this

        # second method of money making: normal garden farming and selling to market

        planted_plant = Gardener.plant(self.plant, min(self.usable_tile_quantity, self.usable_plant_quantity))
        self.usable_tile_quantity -= planted_plant
        planted_fallback_plant = Gardener.plant(self.fallback_plant,
                                                min(self.usable_tile_quantity, self.usable_fallback_plant_quantity))

        # TODO: size of plant should be considered
        sell_amount = self.usable_plant_quantity - GardenManager().get_num_of_plantable_tiles()
        if sell_amount > 0:
            Trader.sell(self.plant, sell_amount)
        sell_amount = self.usable_fallback_plant_quantity - planted_fallback_plant
        if sell_amount > 0:
            Trader.sell(self.fallback_plant, sell_amount)
        if self.prev_plant is not None:
            Trader.sell(self.prev_plant, self.usable_prev_plant_quantity)
        if self.prev_fallback_plant is not None:
            Trader.sell(self.prev_fallback_plant, self.usable_prev_fallback_plant_quantity)

        if self.prev_plant is not None:
            min_quantity = ProductHelper.min_quantity(self.prev_plant)
            potential_quantity = ProductHelper.potential_quantity(self.prev_plant)
            if min_quantity + Market().min_sell_quantity(self.prev_plant) > potential_quantity:
                ReservationManager().free_reservation(self, Resource.PLANT, self.prev_plant)
                self.prev_plant = None
        if self.prev_fallback_plant is not None:
            min_quantity = ProductHelper.min_quantity(self.prev_fallback_plant)
            potential_quantity = ProductHelper.potential_quantity(self.prev_fallback_plant)
            if min_quantity + Market().min_sell_quantity(self.prev_fallback_plant) > potential_quantity:
                ReservationManager().free_reservation(self, Resource.PLANT, self.prev_fallback_plant)
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

        if GardenHelper.get_potential_quantity_of(self.plant) == 0:
            self.sub_objectives.append(ProvidePlant(self.priority, self.plant))

    def __str__(self):
        return f"{self.__class__.__name__}(priority={self.priority}, plant={self.plant}, quantity={self.quantity})"

    def reach_quantity(self):
        if self.consider_min_quantity:
            return ProductHelper.min_quantity(self.plant) + self.quantity
        return self.quantity

    def get_reservations(self):
        self.usable_plant_quantity = ReservationManager().reserve(self, Resource.PLANT, self.reach_quantity(),
                                                                  self.plant)
        return self.usable_plant_quantity != 0

    def is_reached(self):
        return self.usable_plant_quantity >= self.reach_quantity()

    def finish(self):
        ReservationManager().free_reservation(self, Resource.PLANT, self.plant)
        ReservationManager().free_reservation(self, Resource.TILE)
        return True

    def get_work_reservations(self):
        if len(GardenManager().get_empty_tiles()) == 0:
            return False

        missing_amount = self.reach_quantity() - GardenHelper.get_potential_quantity_of(self.plant)
        if missing_amount <= 0:
            self.usable_tile_quantity = 0
            return False
        tile_amount = math.ceil(missing_amount / (self.plant.harvest_quantity - 1))
        if self.usable_plant_quantity < tile_amount:
            tile_amount = self.usable_plant_quantity
        self.usable_tile_quantity = ReservationManager().reserve(self, Resource.TILE, tile_amount)
        return self.usable_tile_quantity != 0

    def work(self):
        Gardener.plant(self.plant, self.usable_tile_quantity)


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
        return AccountData().money - Market().min_money() >= self.product.price_npc * self.quantity

    def get_finish_reservations(self):
        self.usable_money_quantity = ReservationManager().reserve(self, Resource.MONEY,
                                                                  self.product.price_npc * self.quantity)
        return self.usable_money_quantity != 0

    def finish(self):
        Trader.buy_cheapest_of(self.product, self.quantity, self.usable_money_quantity)
        ReservationManager().free_reservation(self, Resource.MONEY)
        return True

    def work(self):
        # work is done by sub objectives and buying the plant is done at finish therefore there is no need to work
        # also this should never be reached, because if so this objectives is in an endless loop
        raise NotImplementedError("Provide plant work function has been reached.")
