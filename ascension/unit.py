from ascension.util import Singleton
from ascension.ascsprite import Sprite, UNIT_GROUP
from ascension.tilemap import TileMap
import logging


LOG = logging.getLogger(__name__)


class UnitSet(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.units = {}

    def new_unit(self, *args, **kwargs):
        unit = Unit(*args, **kwargs)
        self.add_unit(unit)

    def anchor_sprites(self, tilemap=None):
        if tilemap:
            self.tilemap = tilemap
        if not self.tilemap:
            raise Exception("Cannot anchor sprites with no tilemap set")
        for (x, y), units in self.units.items():
            tilesprite = self.tilemap.gettile(x, y).sprite
            x_offset = -15 * (len(units) - 1)
            for unit in units:
                unit.sprite.x = tilesprite.x + x_offset
                unit.sprite.y = tilesprite.y
                unit.sprite.z = tilemap.unit_z
                x_offset += 30

    def add_unit_sprites(self, sprite_manager):
        for units in self.units.values():
            for unit in units:
                unit.add_sprite(sprite_manager)

    def get_units_at(self, x, y):
        if (x, y) not in self.units:
            return []
        return self.units[(x, y)]

    def add_unit(self, unit):
        if (unit.x, unit.y) not in self.units:
            self.units[(unit.x, unit.y)] = []
        self.units[(unit.x, unit.y)].append(unit)

    def move_unit(self, unit, new_x, new_y):
        LOG.info("move {} to ({}, {})".format(unit, new_x, new_y))
        if not TileMap.moverules.isadjacent(unit.x, unit.y, new_x, new_y):
            LOG.info("Move is not adjacent, ignoring move".format(unit, new_x, new_y))


class Unit(object):

    def __init__(self, x, y, name):
        self.x = x
        self.y = y
        self.name = name
        self.make_sprite()
        self.moving = False

    def add_sprite(self, sprite_manager):
        sprite_manager.add_sprite(UNIT_GROUP, self.sprite)


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

