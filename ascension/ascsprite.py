from ascension.util import Singleton
from ascension.settings import AscensionConf as conf
import pyglet
import logging
import yaml
from pyglet import gl
from sprite.component import SpriteComponent
from sprite.animation import SpriteAnimation, SpriteAnimationPlayer, SpriteAnimationStage
from datetime import timedelta
from math import floor


LOG = logging.getLogger(__name__)


class AscSpriteComponent(SpriteComponent):

    def __init__(self, *args, **kwargs):
        super(AscSpriteComponent, self).__init__(*args, **kwargs)
        self.true_center_x, self.true_center_y = None, None
        self.calc_true_center()

    def __setstate__(self, *args, **kwargs):
        super(AscSpriteComponent, self).__setstate__(*args, **kwargs)
        self.calc_true_center()

    def get_anchor(self, anchorname):
        anchor_x, anchor_y = "{}_x".format(anchorname), "{}_y".format(anchorname)
        if anchor_x not in self.extra_meta or anchor_y not in self.extra_meta:
            raise KeyError("Component anchor '{}' not found for component '{}'".format(
                anchorname, self.name
            ))
        return self.extra_meta[anchor_x], self.extra_meta[anchor_y]

    def calc_true_center(self):
        if self.width and self.height:
            self.true_center_x = self.width / 2
            self.true_center_y = self.height /2

    def get_true_center(self):
        return self.true_center_x, self.true_center_y


class AscAnimationStage(SpriteAnimationStage):
    params = [
        {"name": "anchor", "default": "center"}
    ] + SpriteAnimationStage.params

    def __init__(self, *args, **kwargs):
        super(AscAnimationStage, self).__init__(*args, **kwargs)


class AscAnimation(SpriteAnimation):
    stage_class = AscAnimationStage

    def __getstate__(self):
        state = super(AscAnimation, self).__getstate__()
        state["anchor"] = getattr(self, "anchor", "center")
        return state

    def __setstate__(self, state):
        super(AscAnimation, self).__setstate__(state)
        self.anchor = state.get("anchor", "center")
        for stage in self.stages:
            stage.anchor = self.anchor


class Sprite(object):

    def __init__(self, x=0, y=0, component_name=None, level=0):
        self.level = level
        self.x = floor(x)
        self.y = floor(y)
        self.component = None
        self.visible = True
        self.animation = None
        self.animation_player = None
        self.displacement_x = 0
        self.displacement_y = 0
        self.anchor = 0
        if component_name:
            self.set_component(component_name)

    def __cmp__(self, other):
        funcs = [lambda x: x.level, lambda x: -x.y, lambda x: id(x)]
        for func in funcs:
            value = func(self).__cmp__(func(other))
            if value != 0:
                return value
        return 0

    def __unicode__(self):
        return "Sprite(x={x}, y={y}, {component})".format(
            component=self.component_name, x=self.x, y=self.y
        )

    def __str__(self):
        return unicode(self)

    @property
    def component_x(self):
        return self.component and self.component.rect.x

    @property
    def component_y(self):
        return self.component and self.component.rect.y

    @property
    def component_width(self):
        return self.component and self.component.rect.width

    @property
    def component_height(self):
        return self.component and self.component.rect.height

    @property
    def component_name(self):
        return self.component and self.component.name

    @property
    def component_center(self):
        return self.component_width / 2, self.component_height / 2

    def set_component(self, component_name=None, component=None, displacement_x=0, displacement_y=0,
                      duration=None, anchor="center"):
        if not component:
            if not component_name:
                raise ValueError("set_component requires either a component or a component name")
            component = SpriteManager.get_component(component_name)
        self.component = component
        self.compoennt_name = component_name or component.name
        self.duration = duration
        self.anchor = anchor
        self.anchor_x, self.anchor_y = self.component.get_anchor(anchor)
        self.displacement_x = displacement_x
        self.displacement_y = displacement_y

    def get_component_center(self):
        return self.component_width / 2, self.component_height

    def draw(self, offset, scale):
        if not self.component or not self.visible:
            return
        texture = SpriteManager.texture
        texture_width, texture_height = float(texture.width), float(texture.height)
        component_x = self.component_x / texture_width
        component_y = self.component_y / texture_height
        relative_component_width = self.component_width / texture_width
        relative_component_height = self.component_height / texture_height
        width = self.component_width * scale
        height = self.component_height * scale
        offset_x, offset_y = offset
        draw_x = (
            (self.x + self.displacement_x - self.anchor_x + offset_x) * scale
        )
        draw_y = (
            (self.y + self.displacement_y - self.component_height + self.anchor_y + offset_y) * scale
        )
        draw_z = getattr(self, 'z', 0)
        array = (gl.GLfloat * 32)(
            component_x, component_y, 0.0, 1.,
            draw_x, draw_y, draw_z, 1.,
            component_x + relative_component_width, component_y, 0.0, 1.,
            draw_x + width, draw_y, draw_z, 1.,
            component_x + relative_component_width, component_y + relative_component_height, 0.0, 1.,
            draw_x + width, draw_y + height, draw_z, 1.,
            component_x, component_y + relative_component_height, 0.0, 1.,
            draw_x, draw_y + height, draw_z, 1.
        )
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glPushClientAttrib(gl.GL_CLIENT_VERTEX_ARRAY_BIT)
        gl.glInterleavedArrays(gl.GL_T4F_V4F, 0, array)
        gl.glDrawArrays(gl.GL_QUADS, 0, 4)
        gl.glPopClientAttrib()

    def tick(self, time_passed):
        if self.animation_player:
            self.animation_player.pass_animation_time(timedelta(seconds=time_passed))

    def start_animation(self, animation, extra_time=0, override=False, end_callback=None, callbacks={}):
        if self.animation_player and not self.animation_player.iscomplete() and not override:
            raise Exception("{0} set to animation {1} while already in animation {2}".format(
                self, animation, self.animation
            ))
        self.animation = animation
        self.animation_player = SpriteAnimationPlayer(self, self.animation)
        for hook, callback_list in callbacks.items():
            for callback in callback_list:
                self.animation_player.add_callback(hook, callback)
        if end_callback:
            if not isinstance(end_callback, (tuple, list)):
                end_callback = [end_callback]
            for callback in end_callback:
                self.animation_player.add_end_callback(callback)
        self.animation_player.add_end_callback(self.clear_complete_animation)
        self.animation_player.start_animation(extra_time=timedelta(0))

    def clear_complete_animation(self, extra_time):
        if self.animation_player and self.animation_player.iscomplete():
            self.animation_player = None
            self.animation = None


class SpriteManager(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.load_atlas()
        self.sprites = {}
        self.scale = 2.0

    def load_atlas(self):
        self.image = pyglet.image.load(conf.atlas_image)
        with open(conf.atlas_meta) as f:
            atlas_data = yaml.load(f)
        self.components = {}
        for component_data in atlas_data["components"]:
            component = AscSpriteComponent.from_meta(component_data)
            self.components[component.name] = component
        self.animations = {}
        for animation_data in atlas_data["animations"]:
            animation = AscAnimation.load(animation_data)
            for stage in animation.stages:
                stage.component = self.components[stage.component_name]
            self.animations[animation.name] = animation
        self.texture = self.image.get_texture()
        self.reverse_all_component_y()

    def reverse_all_component_y(self):
        for component in self.components.values():
            component.rect.y = self.texture.height - component.rect.y - component.rect.height

    def enable_gl_texture(self):
        gl.glEnable(self.texture.target)
        gl.glBindTexture(self.texture.target, self.texture.id)

    def disable_gl_texture(self):
        gl.glDisable(self.texture.target)

    def get_component(self, component_name):
        return self.components[component_name]

    def add_sprite(self, sprite):
        self.sprites[sprite] = sprite

    def draw_sprites(self, offset):
        SpriteManager.enable_gl_texture()
        offset = [x / self.scale for x in offset]
        for sprite in self.sprites.values():
            sprite.draw(offset, self.scale)
        SpriteManager.disable_gl_texture()

    def tick(self, time_passed):
        for sprite in self.sprites.values():
            sprite.tick(time_passed)
