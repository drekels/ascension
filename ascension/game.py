import logging
import pyglet


import ascension
from ascension.util import Singleton
from ascension.settings import AscensionConf, PlayerConf
from ascension.window import MainWindowManager
from ascension.profiler import ProfilerManager
from ascension.keyboard import KeyboardHandler
from ascension.ascsprite import SpriteManager
from ascension.tilemap import TileMap
from ascension.unit import UnitSet


GREY = (100, 100, 100)
LOG = logging.getLogger(__name__)

FRAME_VERY_LONG_MESSAGE = (
    "Last frame ran for %s seconds!"
)

SLOW_FRAME_MESSAGE = (
    "Last frame ran for {} microseconds, which is over the target {} microseconds ({} fps) by {} "
    "microseconds "
)

class Ascension(object):
    __metaclass__ = Singleton
    components = [
        AscensionConf, PlayerConf, ProfilerManager, SpriteManager, MainWindowManager,
        KeyboardHandler, TileMap, UnitSet
    ]
    tick_listeners = [
        KeyboardHandler, SpriteManager
    ]

    @classmethod
    def _init_all(cls):
        for single in [cls] + cls.components:
            if not single.instance:
                single.reset()
        MainWindowManager.set_keyboard_manager(KeyboardHandler)
        for listener in cls.tick_listeners:
            MainWindowManager.check_add_tick_listener(listener)

    @classmethod
    def start(cls):
        cls._init_all()
        cls.initialize()
        cls.run()

    def __init__(self, *args, **kwargs):
        super(Ascension, self).__init__(*args, **kwargs)

    def initialize(self):
        TileMap.generate_square()
        TileMap.add_tile_sprites(SpriteManager)
        UnitSet.new_unit(1, 1, "spear")
        UnitSet.new_unit(-1, -1, "bow")
        UnitSet.anchor_sprites(TileMap)
        UnitSet.add_unit_sprites(SpriteManager)

    def run(self):
        logging.config.dictConfig(AscensionConf.logging)
        LOG.info("== Starting ASCENSION {} ==".format(ascension.get_version()))
        MainWindowManager.open()
        pyglet.app.run()


if __name__ == "__main__":
    Ascension.start()
