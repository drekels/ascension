from ascension.util import Singleton
from ascension.settings import AscensionConf as conf
import pyglet
import logging
import yaml
from pyglet import gl


LOG = logging.getLogger(__name__)


class Sprite(object):

    def __init__(self, x=0, y=0, component_name=None, scale=2):
        self.x = x
        self.y = y
        self.component = None
        self.scale = scale
        if component_name:
            self.set_component(component_name)

    @property
    def component_x(self):
        return self.component and self.component["x"]

    @property
    def component_y(self):
        return self.component and self.component["y"]

    @property
    def component_width(self):
        return self.component and self.component["width"]

    @property
    def component_height(self):
        return self.component and self.component["height"]

    @property
    def component_name(self):
        return self.component and self.component["name"]

    def set_component(self, component_name):
        self.component = SpriteManager.get_component(component_name)
        self.compoennt_name = component_name

    def draw(self):
        if not self.component:
            return
        texture = SpriteManager.texture
        tw, th = float(texture.width), float(texture.height)
        w, h = self.component_width * self.scale, self.component_height * self.scale
        xn, yn = self.component_x / tw, self.component_y / th
        wn, hn = self.component_width / tw, self.component_height / th
        x, y, z = self.x - w / 2, self.y - h / 2, 0
        array = (gl.GLfloat * 32)(
            xn, yn, 0.0, 1.,
            x, y, z, 1.,
            xn + wn, yn, 0.0, 1.,
            x + w, y, z, 1.,
            xn + wn, yn + hn, 0.0, 1.,
            x + w, y + h, z, 1.,
            xn, yn + hn, 0.0, 1.,
            x, y + h, z, 1.
        )
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glPushClientAttrib(gl.GL_CLIENT_VERTEX_ARRAY_BIT)
        gl.glInterleavedArrays(gl.GL_T4F_V4F, 0, array)
        gl.glDrawArrays(gl.GL_QUADS, 0, 4)
        gl.glPopClientAttrib()


class SpriteManager(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.load_atlas()

    def load_atlas(self):
        self.image = pyglet.image.load(conf.atlas_image)
        with open(conf.atlas_meta) as f:
            components = yaml.load(f)
            self.components = {}
            for component in components:
                self.components[component["name"]] = component
        self.texture = self.image.get_texture()
        self.reverse_all_component_y()

    def reverse_all_component_y(self):
        for component in self.components.values():
            component["y"] = self.texture.height - component["y"] - component["height"]

    def enable_gl_texture(self):
        gl.glEnable(self.texture.target)
        gl.glBindTexture(self.texture.target, self.texture.id)

    def disable_gl_texture(self):
        gl.glDisable(self.texture.target)

    def get_component(self, component_name):
        return self.components[component_name]
