from decimal import Decimal


from tools.util import TerrainGenerator


class GrasslandGenerator(TerrainGenerator):
    perlin_setup = [
        {"weight": Decimal('0.5'), "dimensions": (4, 70), "seed": 32},
        {"weight": Decimal('0.5'), "dimensions": (30, 150), "seed": 89},
    ]
    color_map = [
        (Decimal('0.04'), (156, 124, 33)),
        (Decimal('0.04'), (169, 135, 35)),
        (Decimal('0.25'), (129, 158, 38)),
        (Decimal('0.42'), (138, 169, 40)),
        (Decimal('0.25'), (149, 182, 44)),
    ]
    group_name = "grassland"
    progress_bar_sleep = 1
    border = [
        (0, 0, 0, 1), ((0, 0, 0, 0.2), (255, 255, 255, 0.2))
    ]
