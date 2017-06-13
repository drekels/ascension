import logging
import math
from datetime import timedelta
from decimal import Decimal

from Queue import PriorityQueue
import yaml

from ascension.ascsprite import TILE_GROUP, UNIT_GROUP, Sprite, TextSprite
from ascension.util import Singleton
from ascension.perlin import TileablePerlinGenerator
from ascension.settings import AscensionConf as conf

LOG = logging.getLogger(__name__)


BUNCH_TRANSLATIONS = {
    0: (0, 0),
    1: (-1, 0),
    2: (0, 1),
    3: (-1, 1),
    4: (1, -1),
    5: (0, -1),
    6: (1, 0),
}
DIRECTIONS = {
    'N': (0, 1),
    'S': (0, -1),
    'NW': (-1, 1),
    'SW': (-1, 0),
    'NE': (1, 0),
    'SE': (1, -1),
}


def get_tile_bunch_center(x, y):
    orientation = (x + 5*y) % 7
    xt, yt = BUNCH_TRANSLATIONS[orientation]
    return x + xt, y + yt


class TileMap(object):
    __metaclass__ = Singleton
    tile_width = 71
    tile_height = 30
    horz_point_width = 16

    def __init__(self):
        self.moverules = SimpleHexMoveRules()
        self.reset_tiles()
        self.load_feature_maps()

    def load_feature_maps(self):
        self.feature_maps = {}
        with open(conf.atlas_meta) as f:
            atlas_data = yaml.load(f)
        for name, feature_map_data in atlas_data['feature_maps'].items():
            feature_map = FeatureMap()
            feature_map.__setstate__(feature_map_data)
            self.feature_maps[name] = feature_map

    def reset_tiles(self):
        self.tile_map = {}
        self.tiles = []
        self.count = 0

    def generate_map(self):
        self.generate_square()
        self.determine_outer_limits()
        self.assign_terrain()

    def generate_square(self, width=14):
        self.width, self.height = width, width
        self.min_x = -(self.width - 1) / 2
        self.max_x = (self.width + 1)/ 2
        self.min_y = -(self.height - 1) / 2
        self.max_y = (self.height + 1)/ 2
        for x in range(self.min_x, self.max_x):
            y_offset = -int(math.ceil(x / 2.0))
            for y in range(self.min_y + y_offset, self.max_y + y_offset):
                x_pos, y_pos = self.get_tile_pos(x, y)
                terrain = x % 2 and "sea" or "plains"
                tile = Tile(x, y, x_pos=x_pos, y_pos=y_pos, terrain=terrain)
                self.addtile(tile)

    def determine_outer_limits(self):
        self.max_x_pos, self.min_x_pos = 0, 0
        self.max_y_pos, self.min_y_pos = 0, 0
        for tile in self.tiles:
            self.max_x_pos = tile.x_pos > self.max_x_pos and tile.x_pos or self.max_x_pos
            self.min_x_pos = tile.x_pos < self.min_x_pos and tile.x_pos or self.min_x_pos
            self.max_y_pos = tile.y_pos > self.max_y_pos and tile.y_pos or self.max_y_pos
            self.min_y_pos = tile.y_pos < self.min_y_pos and tile.y_pos or self.min_y_pos

    def assign_terrain(self):
        self.assign_sea()
        self.assign_forests()
        self.assign_mountains()

    def assign_forests(self):
        for tile in [(1, 1), (0, 2), (0, 1), (1, 0)]:
            forest_tile = self.gettile(*tile)
            forest_tile.terrain = 'forest'

    def assign_mountains(self):
        for tile in [(-2, 2), (-3, 2), (-3, 3), (-2, 3)]:
            mountain_tile = self.gettile(*tile)
            mountain_tile.terrain = 'mountain'

    def get_feature_map(self, name):
        return self.feature_maps[name]

    def assign_sea(self):
        top_edge = self.max_y_pos
        bottom_edge = self.min_y_pos - self.tile_height/2
        frame_height = top_edge - bottom_edge
        left_edge = self.min_x_pos - self.tile_width/2 + self.horz_point_width
        right_edge = self.max_x_pos + (self.tile_width+1)/2
        frame_width = right_edge - left_edge
        sea_perlin = TileablePerlinGenerator(dimensions=[4, 4], seed=9)
        bunch_values = {}
        for tile in self.tiles:
            bunch = get_tile_bunch_center(tile.x, tile.y)
            bunch_tile = self.gettile(*bunch)
            if bunch_tile and bunch not in bunch_values:
                perlin_x = (bunch_tile.x_pos - left_edge) / Decimal(frame_width)
                perlin_y = (bunch_tile.y_pos - bottom_edge) / Decimal(frame_height)
                perlin_value = sea_perlin.get_value(perlin_x, perlin_y)
                bunch_values[bunch] = perlin_value
        ordered_bunches = sorted([(j, i) for i, j in bunch_values.items()])
        bunch_terrains = {}
        midpoint = len(ordered_bunches) / 2
        for _, bunch in ordered_bunches[:midpoint]:
            bunch_terrains[bunch] = "sea"
        for _, bunch in ordered_bunches[midpoint:]:
            bunch_terrains[bunch] = "plains"
        for tile in self.tiles:
            bunch = get_tile_bunch_center(tile.x, tile.y)
            bunch = self.get_wrapped_coor(*bunch)
            tile.terrain = bunch and bunch_terrains[bunch] or 'sea'

    def addtile(self, tile):
        if tile.x not in self.tile_map:
            self.tile_map[tile.x] = {}
        elif tile.y in self.tile_map[tile.x]:
            raise KeyError(
                "TileMap already contains a tile for point ({}, {})"
                .format(tile.x, tile.y)
            )
        self.tile_map[tile.x][tile.y] = tile
        self.tiles.append(tile)
        self.count += 1

    def get_wrapped_coor(self, x, y):
        if x not in self.tile_map:
            halfwidth = self.width / 2
            y += ((x + halfwidth) / self.width) * halfwidth
            x = (x + halfwidth) % self.width - halfwidth
            return self.get_wrapped_coor(x, y)
        elif y not in self.tile_map[x]:
            return None
        return x, y

    def gettile(self, x, y):
        coor = self.get_wrapped_coor(x, y)
        if coor:
            x, y = coor
            return self.tile_map[x][y]
        return None

    def hastile(self, x, y):
        return x in self.tile_map and y in self.tile_map[x]

    def get_tile_sprites(self):
        for tile in self.tiles:
            yield tile.get_sprite()

    def add_tile_sprites(self, sprite_manager, anchor=(0, 0)):
        for tile in self.tiles:
            self.add_tile_sprite(tile, sprite_manager)

    def get_vert_x_shift(self):
        return conf.tile_height / 2

    def get_tile_pos(self, x, y, anchor=(0, 0)):
        width, height = self.tile_width, self.tile_height
        x_pos = anchor[0] + x * (width - self.horz_point_width)
        y_pos = anchor[1] + y * height + x * self.get_vert_x_shift()
        return x_pos, y_pos

    def add_tile_sprite(self, tile, sprite_manager):
        s = tile.get_sprite()
        sprite_manager.add_sprite(s)
        for feature_sprite in tile.get_feature_sprites():
            sprite_manager.add_sprite(feature_sprite)

    def get_clicked_tile(self, x, y):
        LOG.debug("Entering get_clicked_tile...")
        LOG.debug("clicked ({}, {})".format(x, y))

        x, y = int(x), int(y)
        horz_point_width = self.horz_point_width

        box_width, box_height = self.tile_width - horz_point_width, self.tile_height / 2
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


class Tile(object):

    def __init__(self, x, y, x_pos, y_pos, terrain, feature_map=None):
        self.terrain = terrain
        self.x, self.y = x, y
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.imgnum = (self.x % 2) * 2 + (self.y - self.x / 2) % 2
        self.sprite = None
        self.coor_sprite = None
        self.feature_map = None

    def get_sprite(self):
        if not self.sprite:
            self.make_sprite()
        return self.sprite

    def get_coor_sprite(self):
        if not self.coor_sprite:
            self.make_coor_sprite()
        return self.coor_sprite

    def get_feature_sprites(self):
        if not hasattr(self, 'feature_sprites'):
            self.make_feature_sprites()
        return self.feature_sprites

    def make_sprite(self):
        component_name = "terrain.grassland"
        if self.terrain == 'sea':
            component_name = "terrain.sea.sea_{:0>2}_00".format(self.imgnum)
        if self.terrain == 'forest':
            self.feature_map = TileMap.get_feature_map('terrain.forest_{}'.format(self.imgnum))
        if self.terrain == 'mountain':
            self.feature_map = TileMap.get_feature_map('terrain.mountain_{}'.format(self.imgnum))
        self.sprite = Sprite(
            x=self.x_pos, y=self.y_pos,
            component_name=component_name,
            z_group=TILE_GROUP,
        )
        if self.terrain == 'sea':
            self.start_tile_animation()

    def start_tile_animation(self, extra_time=timedelta(0)):
        self.sprite.start_animation(
            "terrain.sea.sea_{}".format(self.imgnum), extra_time=extra_time,
            end_callback=self.start_tile_animation
        )

    def make_coor_sprite(self):
        self.coor_sprite = TextSprite(
            font_size=14, text="({}, {})".format(self.x, self.y)
        )

    def make_feature_sprites(self):
        self.feature_sprites = []
        if not self.feature_map:
            return
        for feature_info in self.feature_map.features:
            placeholder = feature_info['name']
            feature_name = self.feature_map.get_feature(self.terrain, placeholder)
            x, y = feature_info['x'], feature_info['y']
            edges = feature_info['edges']
            if all([self.is_similar_terrain(edge) for edge in edges]):
                self.make_feature_sprite(feature_name, x, y)

    def is_similar_terrain(self, direction):
        d = DIRECTIONS[direction]
        other_x = self.x + d[0]
        other_y = self.y + d[1]
        other = TileMap.gettile(other_x, other_y)
        return other.terrain == self.terrain

    def make_feature_sprite(self, feature_name, x, y):
        sprite = Sprite(
            component_name=feature_name, x=x, y=y, z_group=UNIT_GROUP, anchor="stand",
            parent=self.sprite
        )
        self.feature_sprites.append(sprite)

    def __repr__(self):
        return unicode(self)

    def __str__(self):
        return unicode(self)

    def __unicode__(self):
        return "Tile({x}, {y}, {x_pos}, {y_pos}, {terrain})".format(**self.__dict__)


class FeatureMap(object):

    def __init__(self):
        self.features = []

    def __setstate__(self, state):
        self.name = state['name']
        self.features = []
        for feature in state['features']:
            self.features.append(feature)
        self.terrain_feature_pairings = {}
        for pairing in state['terrain_feature_pairing']:
            terrain = pairing['terrain']
            pairings = pairing['pairings']
            self.terrain_feature_pairings[terrain] = pairings

    def get_feature(self, terrain, feature_placeholder):
        return self.terrain_feature_pairings[terrain][feature_placeholder]


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
