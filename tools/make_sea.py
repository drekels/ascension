from decimal import Decimal


from tools.util import TerrainGenerator


class SeaGenerator(TerrainGenerator):
    perlin_setup = [
        {"weight": Decimal('0.7'), "dimensions": (8, 50), "seed": 32},
        {"weight": Decimal('0.3'), "dimensions": (8, 50, 2), "seed": 1},
    ]
    color_map = [
        (Decimal('0.2'), (2, 5, 74)),
        (Decimal('0.2'), (2, 4, 82)),
        (Decimal('0.4'), (2, 2, 90)),
        (Decimal('0.1'), (3, 5, 115)),
        (Decimal('0.1'), (3, 8, 140)),
    ]
    animation_frame_count = 10
    animation_duration = 2
    group_name = "sea"
