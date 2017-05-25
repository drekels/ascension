import logging
import random

from ascension.util import Singleton, insert_sort, IllegalActionException
from ascension.ascsprite import SpriteManager, Sprite, UNIT_GROUP
from ascension.tilemap import TileMap
from ascension.settings import AscensionConf as conf, PlayerConf


LOG = logging.getLogger(__name__)

POSITIONS = {
    "top_left": (-12, 4),
    "top": (3, 4),
    "top_right": (14, 3),
    "bottom_left": (-7, -7),
    "bottom_right": (8, -7),
}
BASE_DELAY = 0.3


class UnitSet(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.unit_groups = []

    def add_unit_group(self, unit_group):
        self.unit_groups.append(unit_group)
        unit_group.add_sprites(SpriteManager)


class UnitGroup(object):

    def __init__(self, x, y, units=[]):
        self.x = x
        self.y = y
        self.units = []
        self.intransit = False
        self.facing = "right"
        self.positions = {}
        for unit_name, position in units:
            self.add_unit(unit_name, position)

    def add_unit(self, name, position):
        unit = Unit(name, self)
        self.units.append(unit)
        self.positions[unit] = position
        insert_sort(self.units)

    def add_sprites(self, sprite_manager):
        tile_position = self.get_tile_position(self.x, self.y)
        for unit in self.units:
            sprite = unit.sprite
            sprite.x, sprite.y = self.get_unit_position(unit, tile_position)
            sprite_manager.add_sprite(sprite)

    def get_unit_position(self, unit, tile_position):
        xdiff, ydiff = POSITIONS[self.positions[unit]]
        xtile, ytile = tile_position

        return  xtile + xdiff, ytile + ydiff

    def get_tile_position(self, x, y):
        tile = TileMap.gettile(x, y)
        return tile.x_pos, tile.y_pos

    def move(self, x, y):
        if self.intransit:
            raise IllegalActionException(
                "Cannot move unit group {}, it is in transit".format(self)
            )
        if not TileMap.hastile(x, y):
            raise IllegalActionException(
                "Cannot move to tile ({}, {}) because it does not exist".format(
                x, y)
            )
        if not TileMap.moverules.isadjacent(self.x, self.y, x, y):
            raise IllegalActionException(
                "Cannot move from ({}, {}) to ({}, {}) as they are not adjacent".format(
                self.x, self.y, x, y)
            )
        self.facing, direction, speed = self.get_move_direction(x, y)
        self.x, self.y = x, y
        self.intransit = True
        self.units_in_transit = []
        position = self.get_tile_position(x, y)
        for unit in self.units:
            self.units_in_transit.append(unit)
            new_position = self.get_unit_position(unit, position)
            unit.move_to(new_position, direction, self.facing, speed)

    def get_move_direction(self, x, y):
        direction = (x - self.x, y - self.y)
        unit_speed = PlayerConf.unit_move_speed
        vert_speed = unit_speed * conf.perspective_sin
        diag_speed = unit_speed * conf.diagonal_distance_multiplier
        values = {
            (1, 0): ("right", "bright", diag_speed),
            (1, -1): ("right", "right", diag_speed),
            (0, -1): (self.facing, self.facing, vert_speed),
            (-1, 0): ("left", "left", diag_speed),
            (-1, 1): ("left", "bleft", diag_speed),
            (0, 1): (self.facing, "b{}".format(self.facing), vert_speed),
        }
        return values[direction]

    def finish_unit_move(self, unit):
        self.units_in_transit.remove(unit)
        if not self.units_in_transit:
            self.intransit = False



class Unit(object):

    def __init__(self, name, unit_group):
        self.name = name
        self.make_sprite()
        self.moving = False
        self.unit_group = unit_group

    def make_sprite(self):
        stand_right = self.get_component("stand_right")
        self.sprite = Sprite(component_name=stand_right, anchor="stand", z_group=UNIT_GROUP)

    def get_component(self, name):
        component_path = ".".join(["unit", self.name, name])
        return component_path

    def __unicode__(self):
        return "Unit({x}, {y}, {name})".format(**self.__dict__)

    def __str__(self):
        return unicode(self)

    def __cmp__(self, other):
        return 0

    def get_move_delay(self):
        return random.random() * BASE_DELAY

    def move_to(self, position, direction, facing, speed):
        self.pending_position = position
        self.pending_speed = speed
        self.pending_animation = self.get_walk_animation(direction)
        self.pending_resting = self.get_component("stand_{}".format(facing))
        delay = self.get_move_delay()
        self.sprite.static_delay(delay, end_callback=self.move_after_delay)

    def move_after_delay(self, time_passed=0.0):
        self.sprite.move_to(
            self.pending_position, self.pending_speed, self.pending_animation,
            resting_component=self.pending_resting, end_callback=self.finish_move
        )

    def finish_move(self, extra_time):
        self.unit_group.finish_unit_move(self)

    def get_walk_animation(self, direction):
        return SpriteManager.get_animation("unit.{}.walk_{}".format(self.name, direction))

    def get_default_walk_animation(self):
        return self.get_walk_animation("right")
