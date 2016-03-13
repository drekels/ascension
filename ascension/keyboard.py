from ascension.util import Singleton
import logging
from pyglet.window import key
from ascension.window import MainWindowManager
from ascension.settings import PlayerConf
from ascension.ascsprite import SpriteManager, OVERLAY_GROUP


LOG = logging.getLogger(__name__)


class KeyboardHandler(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.keys_held = []

    def on_key_press(self, symbol, modifiers):
        keystring, modstring = key.symbol_string(symbol), key.modifiers_string(modifiers)
        LOG.debug("'{}'('{}') Pressed with the following modifiers: {}".format(
            keystring, symbol, modstring)
        )
        if symbol in self.keys_held:
            LOG.warning("Key '{}' was being held but received key pressed event")
        else:
            self.keys_held.append(symbol)
            funcname = "press_{}".format(keystring.lower())
            func = getattr(self, funcname, None)
            if func:
                func()

    def on_key_release(self, symbol, modifiers):
        LOG.debug("'{}' Released with the following modifiers: {}".format(
            key.symbol_string(symbol), key.modifiers_string(modifiers))
        )
        if symbol not in self.keys_held:
            LOG.warning("Key '{}' was not being held but received key pressed event")
        else:
            self.keys_held.remove(symbol)

    def bind_keyboard_events(self, window):
        self.state = key.KeyStateHandler()
        LOG.info("Keyboard events bound to {}".format(self))
        window.event(self.on_key_press)
        window.event(self.on_key_release)
        window.push_handlers(self.state)

    def tick(self, time_passed):
        for symbol in self.keys_held:
            keystring = key.symbol_string(symbol)
            funcname = "tick_{}".format(keystring.lower())
            func = getattr(self, funcname, None)
            if func:
                func(time_passed)
            else:
                LOG.debug("No tick handler found for held key '{}'('{}')".format(keystring, key))

    def tick_up(self, time_passed):
        MainWindowManager.move(0, PlayerConf.scroll_speed * time_passed)
        LOG.debug("MainWindowManager 'y' set to '{}'".format(MainWindowManager.y))

    def tick_down(self, time_passed):
        MainWindowManager.move(0, -PlayerConf.scroll_speed * time_passed)
        LOG.debug("MainWindowManager 'y' set to '{}'".format(MainWindowManager.y))

    def tick_left(self, time_passed):
        MainWindowManager.move(-PlayerConf.scroll_speed * time_passed, 0)
        LOG.debug("MainWindowManager 'x' set to '{}'".format(MainWindowManager.x))

    def tick_right(self, time_passed):
        MainWindowManager.move(PlayerConf.scroll_speed * time_passed, 0)
        LOG.debug("MainWindowManager 'x' set to '{}'".format(MainWindowManager.x))

    def press_o(self):
        SpriteManager.toggle_group_active(OVERLAY_GROUP)

