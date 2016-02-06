from ascension.util import Singleton
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
        unit = None
        for tile in self.tiles:
            units = UnitSet.get_units_at(*tile)
            if units:
                unit = units[0]
                break
        UnitSet.move_unit(unit, *clicked)

    def get_clicked_tile(self, x, y):
        value = self.tiles[self.next_tile]
        self.next_tile = (self.next_tile + 1) % len(self.tiles)
        return value

    def bind_mouse_events(self, window):
        window.event(self.on_mouse_press)
        window.event(self.on_mouse_release)
