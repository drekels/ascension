import logging
import math

from Queue import PriorityQueue

from ascension.ascsprite import OVERLAY_GROUP, TILE_GROUP, UNIT_GROUP, Sprite, TextSprite
from ascension.util import Singleton

LOG = logging.getLogger(__name__)


class TileMap(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.moverules = SimpleHexMoveRules()
        self.reset_tiles()

    def reset_tiles(self):
        self.tiles = {}
        self.count = 0

    def generate_square(self, width=10, height=10):
        min_x = -(width - 1) / 2
        max_x = (width + 1)/ 2
        min_y = -(height - 1) / 2
        max_y = (height + 1)/ 2
        for x in range(min_x, max_x):
            y_offset = -int(math.ceil(x / 2.0))
            for y in range(min_y + y_offset, max_y + y_offset):
                self.addtile(Tile(x, y))

    def addtile(self, tile):
        if tile.x not in self.tiles:
            self.tiles[tile.x] = {}
        elif tile.y in self.tiles[tile.x]:
            raise KeyError(
                "TileMap already contains a tile for point ({}, {})"
                .format(tile.x, tile.y)
            )
        self.tiles[tile.x][tile.y] = tile
        self.count += 1

    def gettile(self, x, y):
        return self.tiles[x][y]

    def hastile(self, x, y):
        return x in self.tiles and y in self.tiles[x]

    def get_tile_sprites(self):
        for column in self.tiles:
            for tile in column:
                yield tile.get_sprite()

    def add_tile_sprites(self, sprite_manager, anchor=(0, 0)):
        for x in self.tiles:
            for y in self.tiles[x]:
                self.add_tile_sprite(x, y, sprite_manager, anchor=anchor)

    def get_horz_point_width(self):
        return 16

    def get_vert_x_shift(self):
        return self.get_tile_height() / 2

    def get_perspective_sin(self):
        if hasattr(self, "perspective_sin"):
            return self.perspective_sin
        i = self.get_vert_x_shift()
        x = self.get_tile_width() / 2.0
        z = self.get_tile_width()/2.0 - self.get_horz_point_width()
        self.perspective_sin = i / math.sqrt(x**2-z**2)
        return self.perspective_sin

    def get_diagonal_speed_multiplier(self):
        if hasattr(self, "diagonal_speed_multiplier"):
            return self.diagonal_speed_multiplier
        self.diagonal_speed_multiplier = math.sqrt(self.get_perspective_sin()**2 + 3) / 2
        return self.diagonal_speed_multiplier

    def get_vert_speed_multiplier(self):
        return self.get_perspective_sin()

    def add_tile_sprite(self, x, y, sprite_manager, anchor=(0, 0)):
        tile = self.tiles[x][y]
        s = tile.get_sprite()
        coor = tile.get_coor_sprite()
        width, height = self.get_tile_width(), self.get_tile_height()
        x_position = anchor[0] + x * (width - self.get_horz_point_width())
        y_position = anchor[1] + y * height + x * self.get_vert_x_shift()
        s.x, s.y, s.z = x_position, y_position, 0.0
        coor.set_position(x_position, y_position)
        sprite_manager.add_sprite(TILE_GROUP, s)
        sprite_manager.add_sprite(OVERLAY_GROUP, coor)
        for feature_sprite in tile.get_feature_sprites():
            feature_sprite.x = feature_sprite.x + x_position
            feature_sprite.y = feature_sprite.y + y_position
            sprite_manager.add_sprite(UNIT_GROUP, feature_sprite)


    def get_tile_width(self):
        return self.tiles[0][0].get_sprite().component_width

    def get_tile_height(self):
        return self.tiles[0][0].get_sprite().component_height

    def get_clicked_tile(self, x, y):
        LOG.debug("Entering get_clicked_tile...")
        LOG.debug("clicked ({}, {})".format(x, y))

        x, y = int(x), int(y)
        horz_point_width = self.get_horz_point_width()
        tile_width, tile_height = self.get_tile_width(), self.get_tile_height()

        LOG.debug("tile dimensions ({}, {})".format(tile_width, tile_height))

        box_width, box_height = tile_width - horz_point_width, tile_height / 2
        box_x, box_y = x / box_width, y / box_height
        extra_x, extra_y = x % box_width, y % box_height
        left = (box_x, (box_y - box_x + 1) / 2)
        right = (box_x + 1, (box_y - box_x) / 2)
        x_adjust = horz_point_width * (extra_y - box_height / 2.0) / box_height
        if (box_y+box_x) % 2:
            x_adjust = -x_adjust
        x_adjusted = extra_x + x_adjust

        LOG.debug("x_adjust ({}, {} -> {})".format(x_adjust, extra_x, x_adjusted))

        value = left
        if x_adjusted > box_width / 2.0:
            value = right

        LOG.debug("result ({}, {})".format(*value))
        LOG.debug("Exiting get_clicked_tile")

        return value

    def get_tile_position(self, x, y):
        tile = self.tiles[x][y]
        return tile.sprite.x, tile.sprite.y


class Tile(object):

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.sprite = None
        self.coor_sprite = None
        self.feature_sprites = None
        self.feature_map = FeatureMap()

    def get_sprite(self):
        if not self.sprite:
            self.make_sprite()
        return self.sprite

    def get_coor_sprite(self):
        if not self.coor_sprite:
            self.make_coor_sprite()
        return self.coor_sprite

    def get_feature_sprites(self):
        if not self.feature_sprites:
            self.make_feature_sprites()
        return self.feature_sprites

    def make_sprite(self):
        self.sprite = Sprite(
            component_name="terrain.grassland",
        )

    def make_coor_sprite(self):
        self.coor_sprite = TextSprite(
            font_size=14, text="({}, {})".format(self.x, self.y)
        )

    def make_feature_sprites(self):
        self.feature_sprites = []
        for feature_name, x, y in self.feature_map.features:
            self.make_feature_sprite(feature_name, x, y)

    def make_feature_sprite(self, feature_name, x, y):
        sprite = Sprite(component_name=feature_name, x=x, y=y, anchor="stand")
        self.feature_sprites.append(sprite)


class FeatureMap(object):

    def __init__(self, feature_counts=None):
        self.feature_counts = feature_counts or {"mountain": 5}
        self.features = []
        self.place_features()


    def place_features(self):
        self.features.append(("terrain.features.mountain_1", 0, 0))
        self.features.append(("terrain.features.mountain_1", 8, 0))
        self.features.append(("terrain.features.mountain_1", -8, 0))
        self.features.append(("terrain.features.mountain_1", 4, -5))
        self.features.append(("terrain.features.mountain_1", -4, -5))
        self.features.append(("terrain.features.mountain_1", 4, 5))


class SimpleHexMoveRules(object):

    def __init__(self):
        self.adjacent_diffs = [
            (1, -1), (-1, 0), (0, -1), (0, 1), (1, 0), (-1, 1)
        ]

    def getadjacent(self, x, y):
        return [(x + i, y + j) for i, j in self.adjacent_diffs]

    def isadjacent(self, from_x, from_y, to_x, to_y):
        return (to_x - from_x, to_y - from_y) in self.adjacent_diffs

    def getcost(self, from_x, from_y, to_x, to_y):
        if self.isadjacent(from_x, from_y, to_x, to_y):
            return 1
        else:
            return None

    def get_distance(self, from_x, from_y, to_x, to_y):
        x_change = to_x - from_x
        y_change = to_y - from_y
        return max([abs(x_change), abs(y_change), abs(x_change - y_change)])


class DijkstraBase(object):

    def __init__(self, move_rules, origin_x, origin_y):
        self.move_rules = move_rules
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.visible_queue = PriorityQueue()
        self.visible_queue.put((0, (origin_x, origin_y)))
        self.costs = {(origin_x, origin_y): 0}
        self.visited = {}

    def run(self):
        while not self.is_done():
            _, (next_x, next_y) = self.visible_queue.get()
            if (next_x, next_y) not in self.visited:
                self.visit_tile(next_x, next_y)

    def visit_tile(self, x, y):
        base_cost = self.costs[(x, y)]
        for a_x, a_y in self.move_rules.getadjacent(x, y):
            cost = base_cost + self.move_rules.getcost(x, y, a_x, a_y)
            if (a_x, a_y) not in self.costs or self.costs[a_x, a_y] > cost:
                self.costs[(a_x, a_y)] = cost
                priority = self.get_visit_priority(cost, a_x, a_y)
                self.visible_queue.put((priority, (a_x, a_y)))
        self.visited[(x, y)] = base_cost

    def get_visit_priority(self, cost, x, y):
        return cost

    def is_done(self):
        raise NotImplementedError()


class AStar(DijkstraBase):

    def __init__(self, move_rules, origin_x, origin_y, target_x, target_y):
        super(AStar, self).__init__(move_rules, origin_x, origin_y)
        self.target_x = target_x
        self.target_y = target_y

    def get_visit_priority(self, cost, x, y):
        return self.move_rules.get_distance(x, y, self.target_x, self.target_y) + cost

    def is_done(self):
        return (self.target_x, self.target_y) in self.visited or not self.visible_queue.qsize()

    def get_cost(self):
        return self.visited[(self.target_x, self.target_y)]
