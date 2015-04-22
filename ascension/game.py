import logging
import pyglet


import ascension
from ascension.util import Singleton
from ascension.settings import AscensionConf
from ascension.window import MainWindowManager
from ascension.profiler import ProfilerManager
from ascension.sprite import SpriteManager


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

    @classmethod
    def start(cls):
        Ascension.reset()
        AscensionConf.reset()
        ProfilerManager.reset()
        SpriteManager.reset()
        Ascension.instance.run()

    def __init__(self, *args, **kwargs):
        super(Ascension, self).__init__(*args, **kwargs)

    def run(self):
        logging.config.dictConfig(AscensionConf.logging)
        LOG.info("== Starting ASCENSION {} ==".format(ascension.get_version()))
        pyglet.clock.set_fps_limit(AscensionConf.target_frame_rate + 5)
        MainWindowManager.reset()
        MainWindowManager.instance.open()
        pyglet.app.run()



if __name__ == "__main__":
    Ascension.start()
