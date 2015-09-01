from ascension.util import Singleton
from ascension.settings import AscensionConf as conf
import pyglet
import logging
import yaml
from pyglet import gl
from sortedcontainers import SortedList


LOG = logging.getLogger(__name__)


class Sprite(object):

    def __init__(self, x=0, y=0, component_name=None, level=0):
        self.level = level
        self.x = x
        self.y = y
        self.component = None
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

    def draw(self, offset, scale):
        if not self.component:
            return
        texture = SpriteManager.texture
        texture_width, texture_height = float(texture.width), float(texture.height)
        component_x = self.component_x / texture_width
        component_y = self.component_y / texture_height
        component_width = self.component_width / texture_width
        component_height = self.component_height / texture_height
        width = self.component_width * scale
        height = self.component_height * scale
        offset_x, offset_y = offset
        draw_x = (self.x  + offset_x) * scale - width / 2
        draw_y = (self.y + offset_y) * scale - height / 2
        draw_z = 0
        array = (gl.GLfloat * 32)(
            component_x, component_y, 0.0, 1.,
            draw_x, draw_y, draw_z, 1.,
            component_x + component_width, component_y, 0.0, 1.,
            draw_x + width, draw_y, draw_z, 1.,
            component_x + component_width, component_y + component_height, 0.0, 1.,
            draw_x + width, draw_y + height, draw_z, 1.,
            component_x, component_y + component_height, 0.0, 1.,
            draw_x, draw_y + height, draw_z, 1.
        )
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glPushClientAttrib(gl.GL_CLIENT_VERTEX_ARRAY_BIT)
        gl.glInterleavedArrays(gl.GL_T4F_V4F, 0, array)
        gl.glDrawArrays(gl.GL_QUADS, 0, 4)
        gl.glPopClientAttrib()

    def __cmp__(self, other):
        funcs = [lambda x: x.level, lambda x: -x.y, lambda x: id(x)]
        for func in funcs:
            value = func(self).__cmp__(func(other))
            if value != 0:
                return value
        return 0

    def __unicode__(self):
        return "Sprite(x={x}, y={y}, {component})".format(
            component=self.component_name, **self.__dict__
        )


class SpriteManager(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.load_atlas()
        self.sprites = SortedList()
        self.scale = 2

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

    def add_sprite(self, sprite):
        self.sprites.add(sprite)

    def draw_sprites(self, offset):
        SpriteManager.enable_gl_texture()
        offset = [x / self.scale for x in offset]
        for sprite in self.sprites:
            sprite.draw(offset, self.scale)
        SpriteManager.disable_gl_texture()
