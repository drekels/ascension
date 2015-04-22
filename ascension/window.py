import pyglet
import logging
import datetime as dt

from pyglet import gl

from ascension.util import Singleton
from ascension.settings import AscensionConf as conf
from ascension.profiler import ProfilerManager
from ascension.sprite import Sprite, SpriteManager


LOG = logging.getLogger(__name__)


class MainWindowManager(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.width = conf.window_width
        self.height = conf.window_height
        self.warn_frame_time = dt.timedelta(0, 1.0 / conf.target_frame_rate)
        self.error_frame_time = self.warn_frame_time * 5
        self.profiler_targets = [
            ("ERROR", self.error_frame_time), ("WARNING", self.warn_frame_time)
        ]
        self.sprite1 = Sprite(100, 100, "creamtile.png")
        self.sprite2 = Sprite(0, 0, "creamtile.png", 1.5)
        self.sprite3 = Sprite(200, 100, "creamtile.png", 3)

    def initializeGL(self):
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glPushAttrib(gl.GL_ENABLE_BIT)

    def open(self):
        self.pyglet_window = pyglet.window.Window(width=self.width, height=self.height)
        self.pyglet_window.event(self.on_draw)
        self.initializeGL()

    def on_draw(self):
        ProfilerManager.start("MAIN_WINDOW_DRAW", targets=self.profiler_targets)
        pyglet.gl.glColor4f(0.4, 0.4, 0.4, 1)
        drawRect(0, 0, self.width, self.height)
        SpriteManager.enable_gl_texture()
        self.sprite1.draw()
        self.sprite2.draw()
        self.sprite3.draw()
        SpriteManager.disable_gl_texture()

        ProfilerManager.stop("MAIN_WINDOW_DRAW")


def drawRect(x, y=None, width=None, height=None):
    if (y, width, height) == (None, None, None):
        x, y, width, height = x
    pyglet.graphics.draw(4, pyglet.gl.GL_QUADS,
        ('v2i', (x, y, x + width, y, x + width, y + height, x, y + height))
    )
