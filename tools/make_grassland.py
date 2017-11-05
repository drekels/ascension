from decimal import Decimal


from tools.util import TerrainGenerator


class GrasslandGenerator(TerrainGenerator):
    perlin_setup = [
        {"weight": Decimal('1.0'), "dimensions": (12, 40), "seed": 64},
    ]
    color_map = [
        (Decimal('0.50'), (65, 131, 32)),
        (Decimal('0.50'), (71, 145, 35)),
    ]
    group_name = "grassland"
    progress_bar_sleep = 1
    border = [
        (0, 0, 0, 1), ((0, 0, 0, 0.2), (255, 255, 255, 0.2))
    ]
