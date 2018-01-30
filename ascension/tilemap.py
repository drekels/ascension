import logging
import math
import random
from datetime import timedelta
from decimal import Decimal

from Queue import PriorityQueue
import yaml

from ascension.ascsprite import (
    TILE_GROUP, UNIT_GROUP, Sprite, TextSprite, SpriteManager,
    SpriteMaster, Callback, TILE_OVERLAY_GROUP, SEA_GROUP
)
from ascension.util import Singleton
from ascension.perlin import TileablePerlinGenerator
from ascension.settings import AscensionConf as conf
from ascension.window import MainWindowManager

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
    'HOME': (0, 0),
    'N': (0, 1),
    'S': (0, -1),
    'NW': (-1, 1),
    'SW': (-1, 0),
    'NE': (1, 0),
    'SE': (1, -1),
}
DIRECTIONS_I = dict([(coor, direction) for direction, coor in DIRECTIONS.items()])



def get_tile_bunch_center(x, y):
    orientation = (x + 5*y) % 7
    xt, yt = BUNCH_TRANSLATIONS[orientation]
    return x + xt, y + yt

def get_tile_bunch_position(x, y):
    center_x, center_y = get_tile_bunch_center(x, y)
    return DIRECTIONS_I[(x - center_x, y - center_y)]


class TileMap(object):
    __metaclass__ = Singleton
    tile_width = 71
    tile_height = 30
    horz_point_width = 16

    def __init__(self):
        self.moverules = SimpleHexMoveRules()
        self.reset_tiles()
        self.load_feature_maps()
        self.new_refresh_stage = 0
        self.remove_refresh_stage = 0

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

    def generate_map(self, width, height, seed=111):
        if width % 14 or height % 14:
            raise Exception("Map width and height must be multiples of 14")
        random.seed(seed)
        self.create_sprite_masters()
        self.generate_square(width=width, height=height)
        self.determine_outer_limits()
        self.assign_terrain()
        if conf.reveal_map:
            self.reveal_map()
        else:
            origin = self.gettile(0, 0)
            origin.explored = True
            origin.edged = True
            for x, y in DIRECTIONS.values():
                tile = self.gettile(x, y)
                tile.explored = True
                tile.edged = True
                for i, j in DIRECTIONS.values():
                    edged_tile = self.gettile(x+i, y+j)
                    edged_tile.edged = True

    def reveal_map(self):
        for tile in self.tiles:
            tile.edged = True
            tile.explored = True

    def create_sprite_masters(self):
        self.sea_sprite_masters = []
        for i in range(conf.frame_tile_count_vert * conf.frame_tile_count_horz):
            animation_name = "terrain.sea.sea_{}".format(i)
            component_name = "terrain.sea.sea_{:0>2}_00".format(i)
            sprite_master = SpriteMaster(component_name=component_name)
            callback = Callback(
                sprite_master.start_animation, animation_name, circular_callback=True
            )
            sprite_master.start_animation(
                animation_name, end_callback=callback
            )
            self.sea_sprite_masters.append(sprite_master)
            SpriteManager.add_sprite(sprite_master)

    def generate_square(self, width=14, height=14):
        self.width, self.height = width, height
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

    def get_feature_map(self, name):
        return self.feature_maps[name]

    def assign_terrain(self):
        self.tiles_left = list(self.tiles)
        self.assign_sea()
        self.assign_mountains()
        self.assign_forests()
        self.assign_village()

    def assign_terrain_perlin(self, terrain, percentage_of_remaining, size_multiplier):
        tile_count = int(len(self.tiles_left) * percentage_of_remaining)
        perlin_width = size_multiplier * self.width / 14
        perlin_height = size_multiplier * self.height / 14
        perlin = TileablePerlinGenerator(dimensions=[perlin_width, perlin_height])
        values_list = []
        for tile in self.tiles_left:
            perlin_value = self.get_map_perlin_value(perlin, tile.x_pos, tile.y_pos)
            values_list.append((perlin_value, tile))
        tile_queue = [x[1] for x in sorted(values_list)[:tile_count]]
        for tile in tile_queue:
            tile.terrain = terrain
            self.tiles_left.remove(tile)

    def assign_mountains(self):
        self.assign_terrain_perlin(
            "mountain", conf.mountain_percentage, conf.mountain_perlin_size_multiplier
        )

    def assign_forests(self):
        self.assign_terrain_perlin(
            "forest", conf.forest_percentage, conf.forest_perlin_size_multiplier
        )

    def get_map_perlin_value(self, perlin, x_pos, y_pos):
        if not hasattr(self, "top_edge"):
            self.generate_map_perlin_helper_values()
        perlin_x = (x_pos - self.left_edge) / Decimal(self.frame_width)
        perlin_y = (y_pos - self.bottom_edge) / Decimal(self.frame_height)
        return perlin.get_value(perlin_x, perlin_y)

    def generate_map_perlin_helper_values(self):
        self.top_edge = self.max_y_pos
        self.bottom_edge = self.min_y_pos - self.tile_height/2
        self.frame_height = self.top_edge - self.bottom_edge
        self.left_edge = self.min_x_pos - self.tile_width/2 + self.horz_point_width
        self.right_edge = self.max_x_pos + (self.tile_width+1)/2
        self.frame_width = self.right_edge - self.left_edge

    def assign_sea(self):
        perlin_width = conf.sea_perlin_size_multiplier * self.width / 14
        perlin_height = conf.sea_perlin_size_multiplier * self.height / 14
        sea_perlin = TileablePerlinGenerator(dimensions=[perlin_width, perlin_height])
        bunch_values = {}
        for tile in self.tiles_left:
            bunch = get_tile_bunch_center(tile.x, tile.y)
            bunch_tile = self.gettile(*bunch)
            if bunch_tile and bunch not in bunch_values:
                perlin_value = self.get_map_perlin_value(sea_perlin, bunch_tile.x_pos, bunch_tile.y_pos)
                bunch_values[bunch] = perlin_value
        ordered_bunches = sorted([(j, i) for i, j in bunch_values.items()])
        bunch_terrains = {}
        midpoint = int(len(ordered_bunches) * conf.sea_percentage)
        for _, bunch in ordered_bunches[:midpoint]:
            bunch_terrains[bunch] = "sea"
        for _, bunch in ordered_bunches[midpoint:]:
            bunch_terrains[bunch] = "plains"
        for tile in self.tiles:
            bunch = get_tile_bunch_center(tile.x, tile.y)
            bunch = self.get_wrapped_coor(*bunch)
            tile.terrain = bunch and bunch_terrains[bunch] or 'sea'
            if tile.terrain == 'sea':
                self.tiles_left.remove(tile)

    def assign_village(self):
        for tile in [(-2, 5)]:
            self.gettile(*tile).locale = "village"

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

    def get_vert_x_shift(self):
        return conf.tile_height / 2

    def get_tile_pos(self, x, y, anchor=(0, 0)):
        width, height = self.tile_width, self.tile_height
        x_pos = anchor[0] + x * (width - self.horz_point_width)
        y_pos = anchor[1] + y * height + x * self.get_vert_x_shift()
        return x_pos, y_pos

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

    def explore_after_move_to(self, x, y):
        to_edge = []
        for i, j in DIRECTIONS.values():
            x1, y1 = x+i, y+j
            tile = self.gettile(x1, y1)
            if tile and not tile.explored:
                tile.explore((x, y))
                if (x1, y1) in to_edge:
                    to_edge.remove((x1, y1))
                for k, l in DIRECTIONS.values():
                    x2, y2 = x1+k, y1+l
                    edge_tile = self.gettile(x2, y2)
                    if (    edge_tile
                        and not edge_tile.edged
                        and not edge_tile.explored
                        and (x2, y2) not in to_edge
                       ):
                        to_edge.append((x2, y2))
        for e in to_edge:
            tile = self.gettile(*e)
            tile.edge()

    def get_new_sprites(self):
        for i in range(self.new_refresh_stage, len(self.tiles), conf.tilemap_refresh_stages):
            tile = self.tiles[i]
            for sprite in tile.get_new_sprites():
                yield sprite
        self.new_refresh_stage = (self.new_refresh_stage + 1) % conf.tilemap_refresh_stages

    def get_sprites_to_remove(self):
        for i in range(self.remove_refresh_stage, len(self.tiles), conf.tilemap_refresh_stages):
            tile = self.tiles[i]
            for sprite in tile.get_sprites_to_remove():
                yield sprite
        self.remove_refresh_stage = (self.remove_refresh_stage + 1) % conf.tilemap_refresh_stages


class Tile(object):

    def __init__(self, x, y, x_pos, y_pos, terrain, feature_map=None):
        self.terrain = terrain
        self.x, self.y = x, y
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.imgnum = (self.x % 2) * 2 + (self.y - self.x / 2) % 2
        self.sprite = None
        self.shroud_sprite = None
        self.shroud_gone = False
        self.coor_sprite = None
        self.feature_map = None
        self.locale = None
        self.explored = False
        self.edged = False
        self.is_in_view = False
        self.tile_bunch_direction = get_tile_bunch_position(self.x, self.y)
        self.tile_bunch_center = get_tile_bunch_center(self.x, self.y)
        self.feature_sprites = None

    def get_neighbor(self, direction):
        xd, yd = DIRECTIONS[direction]
        return TileMap.gettile(self.x + xd, self.y + yd)

    def get_new_sprites(self):
        self.is_in_view = MainWindowManager.is_position_in_view(
            self.x_pos, self.y_pos, conf.tile_width * 1.5, conf.tile_height * 3.0
        )
        if not self.is_in_view:
            pass
        elif self.explored and not self.sprite:
            self.make_sprite()
            yield self.sprite
        elif self.edged and not self.explored and not self.shroud_sprite:
            self.make_shroud_sprite()
            yield self.shroud_sprite

    def get_sprites_to_remove(self):
        if not self.is_in_view:
            if self.shroud_sprite:
                yield self.shroud_sprite
                self.shroud_sprite = None
            if self.sprite:
                yield self.sprite
                self.feature_sprites = []
                self.sprite = None
        elif self.shroud_sprite and self.shroud_gone:
            yield self.shroud_sprite
            self.shroud_sprite = None

    def make_sprite(self):
        component_name = "terrain.grassland.grassland_{:0>2}_00".format(self.imgnum)
        master = None
        if self.terrain == 'sea':
            master = TileMap.sea_sprite_masters[self.imgnum]
        elif self.terrain == 'forest':
            self.feature_map = TileMap.get_feature_map('terrain.forest_{}'.format(self.imgnum))
        elif self.terrain == 'mountain':
            self.feature_map = TileMap.get_feature_map('terrain.mountain_{}'.format(self.imgnum))

        self.sprite = Sprite(
            x=self.x_pos, y=self.y_pos, master=master, component_name=component_name,
            z_group=self.get_z_group(),
        )

        self.make_feature_sprites()

        if self.locale == 'village':
            self.make_locale_sprite()

    def get_z_group(self):
        return self.terrain == 'sea' and SEA_GROUP or TILE_GROUP

    def start_tile_animation(self, extra_time=timedelta(0)):
        self.sprite.start_animation(
            "terrain.sea.sea_{}".format(self.imgnum), extra_time=extra_time,
            end_callback=self.start_tile_animation
        )

    def explore(self, source):
        self.explored = True
        if self.shroud_sprite:
            self.remove_shroud(source)

    def edge(self):
        self.edged = True
        self.shroud_gone = False

    def remove_shroud(self, source):
        dir_x = self.x - source[0]
        dir_y = self.y - source[1]
        dest_x = self.x + dir_x
        dest_y = self.y + dir_y
        speed = conf.get_speed_multiplier((dir_x, dir_y)) * conf.shroud_move_speed
        self.shroud_sprite.move_to(
            TileMap.get_tile_pos(dest_x, dest_y), speed
        )
        self.shroud_sprite.fade(
            static_delay=conf.shroud_fade_delay, duration=conf.shroud_fade_time,
            end_callback=self.set_shroud_to_gone,
        )

    def set_shroud_to_gone(self, extra_time=None):
        self.shroud_gone = True

    def make_shroud_sprite(self):
        self.shroud_sprite = Sprite(
            x=self.x_pos, y=self.y_pos, component_name="terrain.shroud",
            z_group=UNIT_GROUP,
        )

    def make_coor_sprite(self):
        self.coor_sprite = TextSprite(
            font_size=14, text="({}, {})".format(self.x, self.y)
        )

    def make_feature_sprites(self):
        self.feature_sprites = []
        if self.terrain == 'sea':
            self.make_sea_borders()
            self.make_shores()
        if not self.feature_map:
            return

        for feature_info in self.feature_map.features:
            placeholder = feature_info['name']
            feature_name = self.feature_map.get_feature(self.terrain, placeholder)
            x, y = feature_info['x'], feature_info['y']
            edges = feature_info['edges']
            if all([self.is_similar_terrain(edge) for edge in edges]):
                self.make_feature_sprite(feature_name, x, y)

    def make_sea_borders(self):
        sprite_names = [
            ('S', "terrain.features.sea_border_s"),
            ('SW', "terrain.features.sea_border_sw"),
            ('NW', "terrain.features.sea_border_nw"),
        ]
        for direction, sprite_name in sprite_names:
            neighbor = self.get_neighbor(direction)
            if (    neighbor
                and neighbor.terrain == 'sea'
                and neighbor.tile_bunch_center != self.tile_bunch_center
               ):
                self.make_feature_sprite(
                    sprite_name, 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
                )

    def make_shores(self):
        neighbor_terrain = dict(
            [(x, self.get_neighbor(x) and self.get_neighbor(x).terrain) for x in DIRECTIONS]
        )
        if neighbor_terrain["N"] != "sea" and neighbor_terrain["NW"] == "sea":
            self.make_feature_sprite(
                "terrain.features.shore_out_sw", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["N"] != "sea" and neighbor_terrain["NE"] == "sea":
            self.make_feature_sprite(
                "terrain.features.shore_out_se", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["SW"] != "sea" and neighbor_terrain["S"] == "sea":
            self.make_feature_sprite(
                "terrain.features.shore_out_e", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["S"] != "sea" and neighbor_terrain["SE"] == "sea":
            self.make_feature_sprite(
                "terrain.features.shore_out_ne", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["S"] != "sea" and neighbor_terrain["SW"] == "sea":
            self.make_feature_sprite(
                "terrain.features.shore_out_nw", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["SE"] != "sea" and neighbor_terrain["S"] == "sea":
            self.make_feature_sprite(
                "terrain.features.shore_out_w", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["S"] != "sea" and neighbor_terrain["SW"] != "sea":
            self.make_feature_sprite(
                "terrain.features.shore_in_sw", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["S"] != "sea" and neighbor_terrain["SE"] != "sea":
            self.make_feature_sprite(
                "terrain.features.shore_in_se", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["SE"] != "sea" and neighbor_terrain["NE"] != "sea":
            self.make_feature_sprite(
                "terrain.features.shore_in_e", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["N"] != "sea" and neighbor_terrain["NE"] != "sea":
            self.make_feature_sprite(
                "terrain.features.shore_in_ne", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["SW"] != "sea" and neighbor_terrain["NW"] != "sea":
            self.make_feature_sprite(
                "terrain.features.shore_in_w", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )
        if neighbor_terrain["NW"] != "sea" and neighbor_terrain["N"] != "sea":
            self.make_feature_sprite(
                "terrain.features.shore_in_nw", 0, 0, anchor="tile", z_group=TILE_OVERLAY_GROUP
            )


    def is_similar_terrain(self, direction):
        d = DIRECTIONS[direction]
        other_x = self.x + d[0]
        other_y = self.y + d[1]
        other = TileMap.gettile(other_x, other_y)
        return other is not None and other.terrain == self.terrain

    def make_locale_sprite(self):
        component_name = "locale.{}".format(self.locale)
        sprite = Sprite(
            component_name=component_name, x=0, y=0, z_group=UNIT_GROUP, anchor="tile",
            parent=self.sprite,
        )
        self.locale_sprite = sprite

    def make_feature_sprite(self, feature_name, x, y, anchor="stand", z_group=UNIT_GROUP):
        sprite = Sprite(
            component_name=feature_name, x=x, y=y, z_group=z_group, anchor=anchor,
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
        if x_change * y_change <= 0:
            return max([abs(x_change), abs(y_change)])
        else:
            return abs(x_change + y_change)


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
