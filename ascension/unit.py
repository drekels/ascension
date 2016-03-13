from ascension.util import Singleton, insert_sort, IllegalActionException
from ascension.ascsprite import SpriteManager, Sprite, UNIT_GROUP
from ascension.tilemap import TileMap
from ascension.settings import PlayerConf
import logging


LOG = logging.getLogger(__name__)


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
        for unit_name in units:
            self.add_unit(unit_name)

    def add_unit(self, name):
        unit = Unit(name, self)
        self.units.append(unit)
        insert_sort(self.units)

    def add_sprites(self, sprite_manager):
        px, py = self.get_tile_position()
        for unit in self.units:
            sprite = unit.sprite
            sprite.x = px
            sprite.y = py
            sprite_manager.add_sprite(UNIT_GROUP, sprite)

    def get_tile_position(self):
        return TileMap.get_tile_position(self.x, self.y)

    def move(self, x, y):
        if self.intransit:
            raise IllegalActionException(
                "Cannot move unit group {}, it is intransit".format(self)
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
        position = TileMap.get_tile_position(x, y)
        for unit in self.units:
            self.units_in_transit.append(unit)
            unit.move_to(position, direction, self.facing, speed)

    def get_move_direction(self, x, y):
        direction = (x - self.x, y - self.y)
        unit_speed = PlayerConf.unit_move_speed
        vert_speed = unit_speed * TileMap.get_vert_speed_multiplier()
        diag_speed = unit_speed * TileMap.get_diagonal_speed_multiplier()
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
        self.sprite = Sprite(component_name=stand_right, anchor="stand")

    def get_component(self, name):
        component_path = ".".join(["unit", self.name, name])
        return component_path

    def __unicode__(self):
        return "Unit({x}, {y}, {name})".format(**self.__dict__)

    def __str__(self):
        return unicode(self)

    def __cmp__(self, other):
        return 0

    def move_to(self, position, direction, facing, speed):
        animation = self.get_walk_animation(direction)
        resting = self.get_component("stand_{}".format(facing))
        self.sprite.move_to(
            position, speed, animation, resting_component=resting,
            end_callback=self.finish_move
        )

    def finish_move(self, extra_time):
        self.unit_group.finish_unit_move(self)

    def get_walk_animation(self, direction):
        return SpriteManager.get_animation("unit.{}.walk_{}".format(self.name, direction))
