from wurzelbot.gardens.gardens import GardenManager


class ProductHelper:
    @staticmethod
    def min_quantity(product):
        if product.is_plant():
            return int(GardenManager().get_num_of_plantable_tiles() / (product.size[0] * product.size[1]))
        return 0

    @staticmethod
    def potential_quantity(product):
        from wurzelbot.gardens.garden_helper import GardenHelper
        return GardenHelper.get_potential_quantity_of(product)

    @staticmethod
    def is_min_quantity(product):
        return ProductHelper.min_quantity(product) <= product.quantity

    @staticmethod
    def is_potential_min_quantity(product):
        return ProductHelper.potential_quantity(product) >= ProductHelper.min_quantity(product)
