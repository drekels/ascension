import logging
import pyglet


import ascension
from ascension.util import Singleton
from ascension.settings import AscensionConf, PlayerConf
from ascension.window import MainWindowManager
from ascension.profiler import ProfilerManager
from ascension.keyboard import KeyboardHandler
from ascension.sprite import SpriteManager
from ascension.tilemap import TileMap


GREY = (100, 100, 100)
LOG = logging.getLogger(__name__)

FRAME_VERY_LONG_MESSAGE = (
    "Last frame ran for %s seconds!"
)

SLOW_FRAME_MESSAGE = (
    "Last frame ran for {} microseconds, which is over the target {} microseconds ({} fps) by {} "
    "microseconds "
)

SINGLETONS = [
    AscensionConf, PlayerConf, ProfilerManager, SpriteManager, MainWindowManager,
    KeyboardHandler, TileMap
]
TICK_LISTENERS = [
    KeyboardHandler
]


class Ascension(object):
    __metaclass__ = Singleton

    @classmethod
    def init_all(cls):
        for single in [Ascension] + SINGLETONS:
            if not single.instance:
                single.reset()
        MainWindowManager.set_keyboard_manager(KeyboardHandler)
        for listener in TICK_LISTENERS:
            MainWindowManager.check_add_tick_listener(listener)
        TileMap.generate_square()
        TileMap.add_tile_sprites(SpriteManager)


    @classmethod
    def start(cls):
        cls.init_all()
        Ascension.instance.run()

    def __init__(self, *args, **kwargs):
        super(Ascension, self).__init__(*args, **kwargs)

    def run(self):
        logging.config.dictConfig(AscensionConf.logging)
        LOG.info("== Starting ASCENSION {} ==".format(ascension.get_version()))
        MainWindowManager.open()
        pyglet.app.run()



if __name__ == "__main__":
    Ascension.start()