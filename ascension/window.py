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

    def __init__(self):
        self.width = conf.window_width
        self.height = conf.window_height
        self.warn_frame_time = dt.timedelta(0, 1.0 / conf.target_frame_rate)
        self.error_frame_time = self.warn_frame_time * 5
        self.profiler_targets = [
            ("ERROR", self.error_frame_time), ("WARNING", self.warn_frame_time),
        ]
        self.x, self.y = 0.0, 0.0
        self.pyglet_window = None
        self.count = 0
        self.tick_listeners = []
        self.set_background_color()
        self.position_updated = True
        self.sprite_view_width = conf.fixed_scroller_width
        self.sprite_view_height = conf.fixed_scroller_height

    def tick(self, time_passed):
        ProfilerManager.start("TICK")
        LOG.debug("Tick called, {:.4f}s".format(time_passed))
        for listener in self.tick_listeners:
            listener.tick(time_passed)
        ProfilerManager.stop("TICK")

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

    def set_mouse_manager(self, mouse_manager):
        self.mouse_manager = mouse_manager
        if self.pyglet_window:
            LOG.info("Binding mouse events set")
            mouse_manager.bind_mouse_events(self.pyglet_window)

    def move(self, x, y):
        self.x += x
        self.y += y
        self.xdiff += x
        self.ydiff += y
        self.position_updated = True

    def open(self):
        LOG.info("Window '{}' opened".format(self))
        self.pyglet_window = pyglet.window.Window(
            width=self.width, height=self.height, vsync=False
        )
        self.on_resize(self.width, self.height)
        self.pyglet_window.event(self.on_draw)
        self.pyglet_window.event(self.on_close)
        self.pyglet_window.event(self.on_resize)
        self.xdiff = -self.pyglet_window.width / conf.sprite_scale / 2
        self.ydiff = -self.pyglet_window.height / conf.sprite_scale / 2
        self.initializeGL()
        if self.keyboard_manager:
            LOG.info("Binding keyboard events open")
            self.keyboard_manager.bind_keyboard_events(self.pyglet_window)
        if self.mouse_manager:
            LOG.info("Binding mouse events set")
            self.mouse_manager.bind_mouse_events(self.pyglet_window)
        clock.schedule_interval(self.tick, 1.0 / conf.target_frame_rate)

    def on_draw(self):
        try:
            ProfilerManager.start("MAIN_WINDOW_DRAW", targets=self.profiler_targets)
            self.pyglet_window.clear()
            if self.position_updated:
                self.translate()
            SpriteManager.draw_sprites()
            ProfilerManager.stop("MAIN_WINDOW_DRAW")
        except Exception as e:
            LOG.exception(e)
            from ascension.game import get_game
            import signal
            get_game().quit(signal.SIGQUIT)

    def on_resize(self, width, height):
        if conf.scroller_mode == "DYNAMIC":
            self.sprite_view_width = float(width) / conf.sprite_scale / 2
            self.sprite_view_height = float(height) / conf.sprite_scale / 2

    def translate(self):
        xdiffint = int(self.xdiff * conf.sprite_scale)
        ydiffint = int(self.ydiff * conf.sprite_scale)
        gl.glTranslatef(-xdiffint, -ydiffint, 0.0)
        self.xdiff -= float(xdiffint) / conf.sprite_scale
        self.ydiff -= float(ydiffint) / conf.sprite_scale
        self.position_updated = False

    def get_window_offset(self):
        return (
            self.pyglet_window.width / 2 - self.x * conf.sprite_scale,
            self.pyglet_window.height / 2 - self.y * conf.sprite_scale,
        )

    def check_add_tick_listener(self, listener):
        if listener not in self.tick_listeners:
            self.tick_listeners.append(listener)

    def set_background_color(self, r=0.05, g=0.05, b=0.05):
        self.background_color = (r, g, b, 1)

    def get_sprite_from_screen(self, x, y):
        offset = self.get_window_offset()
        return SpriteManager.get_adjusted_position(x, y, offset)

    def on_close(self):
        LOG.info("User closed window")
        from ascension.game import Ascension as game
        game.quit(None, None)

    def is_position_in_view(self, x, y, extra_x=0.0, extra_y=0.0):
        xdiff = abs(x - self.x) - extra_x
        ydiff = abs(y - self.y) - extra_y
        return xdiff <= self.sprite_view_width and ydiff <= self.sprite_view_height


def drawRect(x, y=None, width=None, height=None):
    if (y, width, height) == (None, None, None):
        x, y, width, height = x
    pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
        ('v2i', (x, y, x + width, y, x + width, y + height, x, y + height))
    )
