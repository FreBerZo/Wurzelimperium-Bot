from src.Garten import garden_manager
from src.Garten import GARDEN_WIDTH
from src.Garten import GARDEN_HEIGHT


class Gardener:
    def can_be_planted_now(self, product):
        size = (product.getSX(), product.getSY())
        for garden in garden_manager.gardens:
            for x in range(GARDEN_WIDTH):
                for y in range(GARDEN_HEIGHT):
                    if garden.plant_fits_at(size, x, y):
                        return True
        return False


gardener = Gardener()
        