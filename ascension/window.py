from __future__ import absolute_import

import pyglet
import logging
import datetime as dt

from pyglet import gl
from pyglet import clock

from ascension.util import Singleton
from ascension.settings import AscensionConf as conf
from ascension.profiler import ProfilerManager
from ascension.ascsprite import SpriteManager


LOG = logging.getLogger(__name__)


class MainWindowManager(object):
    __metaclass__ = Singleton
    default_scale = 2

    def __init__(self):
        self.width = conf.window_width
        self.height = conf.window_height
        self.warn_frame_time = dt.timedelta(0, 1.0 / conf.target_frame_rate)
        self.error_frame_time = self.warn_frame_time * 5
        self.profiler_targets = [
            ("ERROR", self.error_frame_time), ("WARNING", self.warn_frame_time)
        ]
        self.x, self.y = 0.0, 0.0
        self.pyglet_window = None
        self.count = 0
        self.tick_listeners = []
        self.set_background_color()

    def tick(self, time_passed):
        LOG.debug("Tick called, {:.4f}s".format(time_passed))
        for listener in self.tick_listeners:
            listener.tick(time_passed)

    def initializeGL(self):
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glPushAttrib(gl.GL_ENABLE_BIT)

    def set_keyboard_manager(self, keyboard_manager):
        self.keyboard_manager = keyboard_manager
        if self.pyglet_window:
            LOG.info("Binding keyboard events set")
            keyboard_manager.bind_keyboard_events(self.pyglet_window)

    def move(self, x, y):
        self.x += x
        self.y += y

    def open(self):
        LOG.info("Window '{}' opened".format(self))
        self.pyglet_window = pyglet.window.Window(width=self.width, height=self.height, vsync=False)
        self.pyglet_window.event(self.on_draw)
        self.initializeGL()
        if self.keyboard_manager:
            LOG.info("Binding keyboard events open")
            self.keyboard_manager.bind_keyboard_events(self.pyglet_window)
        clock.schedule_interval(self.tick, 1.0 / (conf.target_frame_rate * 3))

    def on_draw(self):
        ProfilerManager.start("MAIN_WINDOW_DRAW", targets=self.profiler_targets)
        pyglet.gl.glColor4f(*self.background_color)
        drawRect(0, 0, self.width, self.height)
        pyglet.gl.glColor4f(1, 1, 1, 1)
        SpriteManager.draw_sprites(self.get_window_offset())
        ProfilerManager.stop("MAIN_WINDOW_DRAW")

    def get_window_offset(self):
        return (
            self.pyglet_window.width / 2 - int(self.x),
            self.pyglet_window.height / 2 - int(self.y),
        )

    def check_add_tick_listener(self, listener):
        if listener not in self.tick_listeners:
            self.tick_listeners.append(listener)

    def set_background_color(self, r=0.05, g=0.05, b=0.05):
        self.background_color = (r, g, b, 1)


def drawRect(x, y=None, width=None, height=None):
    if (y, width, height) == (None, None, None):
        x, y, width, height = x
    pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
        ('v2i', (x, y, x + width, y, x + width, y + height, x, y + height))
    )
