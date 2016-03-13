from ascension.util import Singleton
from ascension.window import MainWindowManager
from ascension.tilemap import TileMap
from ascension.unit import UnitSet
import logging


LOG = logging.getLogger(__name__)


class MouseHandler:
    __metaclass__ = Singleton

    def __init__(self):
        self.press_point = None
        self.next_tile = 0
        self.tiles = [(0, 0), (1, 0), (0, -1), (-1, -1)]

    def on_mouse_press(self, x, y, button, modifiers):
        LOG.debug("mouse pressed {} {} {} {}".format(x, y, button, modifiers))

    def on_mouse_release(self, x, y, button, modifiers):
        LOG.debug("mouse released {} {} {} {}".format(x, y, button, modifiers))
        clicked = self.get_clicked_tile(x, y)
        unit_set = UnitSet.unit_groups[0]
        unit_set.move(*clicked)

    def get_clicked_tile(self, x, y):
        sprite_x, sprite_y = MainWindowManager.get_sprite_from_screen(x, y)
        return TileMap.get_clicked_tile(sprite_x, sprite_y)

    def bind_mouse_events(self, window):
        window.event(self.on_mouse_press)
        window.event(self.on_mouse_release)
