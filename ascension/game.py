import logging
import pyglet
import signal
import sys
from time import sleep


import ascension
from ascension.util import Singleton
from ascension.settings import AscensionConf as conf, PlayerConf
from ascension.window import MainWindowManager
from ascension.profiler import ProfilerManager
from ascension.keyboard import KeyboardHandler
from ascension.mouse import MouseHandler
from ascension.ascsprite import SpriteManager
from ascension.tilemap import TileMap
from ascension.unit import UnitSet, UnitGroup


GREY = (100, 100, 100)
LOG = logging.getLogger(__name__)

FRAME_VERY_LONG_MESSAGE = (
    "Last frame ran for %s seconds!"
)

SLOW_FRAME_MESSAGE = (
    "Last frame ran for {} microseconds, which is over the target {} microseconds ({} fps) by {} "
    "microseconds "
)


GAME = None


def get_game():
    return GAME


class Ascension(object):
    __metaclass__ = Singleton
    components = [
        conf, PlayerConf, ProfilerManager, SpriteManager, MainWindowManager,
        KeyboardHandler, MouseHandler, TileMap, UnitSet
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
        MainWindowManager.set_mouse_manager(MouseHandler)
        for listener in cls.tick_listeners:
            MainWindowManager.check_add_tick_listener(listener)
        SpriteManager.initialize()

    @classmethod
    def start(cls, *args):
        cls._init_all()
        logging.config.dictConfig(conf.logging)
        cls.initialize(*args)
        cls.run()

    def __init__(self, *args, **kwargs):
        global GAME
        GAME = self
        super(Ascension, self).__init__(*args, **kwargs)

    def initialize(self):
        self.setup_signal()
        try:
            TileMap.generate_map(width=conf.map_width, height=conf.map_height)
            unit_group = UnitGroup(0, 0, units=[
                ("sword", "top_left"),
                ("spear", "top"),
                ("bow", "bottom_left"),
                ("sword", "bottom_right"),
            ])
            UnitSet.add_unit_group(unit_group)
            SpriteManager.add_sprite_source(TileMap)
            SpriteManager.add_sprite_source(UnitSet)

        except Exception as e:
            LOG.exception(e)
            self.quit(signal.SIGQUIT, None)

    def run(self):
        LOG.info("== Starting ASCENSION {} ==".format(ascension.get_version()))
        MainWindowManager.open()
        pyglet.app.run()

    def setup_signal(self):
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGQUIT, self.quit)
        signal.signal(signal.SIGTERM, self.kill)

    def quit(self, signal, frame=None):
        LOG.info("Received signal '{}', quiting Ascension ... ".format(signal))
        waiting_for = []
        for component in self.components:
            if hasattr(component, "quit"):
                component.quit()
                waiting_for.append(component)
        time_waited = 0.0
        while waiting_for:
            sleep(conf.quit_sleep)
            time_waited += conf.quit_sleep
            for component in waiting_for:
                if not component.alive():
                    waiting_for.remove(component)
            if time_waited > conf.max_quit_wait_time:
                LOG.error("The components {} failed to quit properly".format(waiting_for))
        LOG.info("Quit Complete")
        sys.exit(0)

    def kill(self, signal, frame):
        LOG.info("Received signal '{}', killing Ascension ... ".format(signal))
        for component in self.components:
            try:
                if hasattr(component, "kill"):
                    component.kill()
            except Exception:
                pass
        LOG.info("Kill complete")
        sys.exit(0)


if __name__ == "__main__":
    Ascension.start()
