import pyglet
import logging
import yaml
from datetime import timedelta
from math import floor, ceil

from pyglet import gl
from pyglet.text import Label
from sprite.component import SpriteComponent
from sprite.animation import (
    SpriteAnimation, SpriteAnimationPlayer, SpriteAnimationStage, ON_ANIMATION_END
)

from ascension.util import Singleton, insert_sort
from ascension.settings import AscensionConf as conf
from ascension.profiler import ProfilerManager

LOG = logging.getLogger(__name__)


TILE_GROUP = 100
UNIT_GROUP = 200
OVERLAY_GROUP = 300
ON_TRANSITION_END = ON_ANIMATION_END


class TransitionEngine(object):

    def __init__(self, sprite):
        self.callbacks = {}
        self.sprite = sprite

    def add_callback(self, hook, callback):
        try:
            iter(callback)
            callbacks = callback
        except TypeError:
            callbacks = [callback]
        if hook not in self.callbacks:
            self.callbacks[hook] = []
        for cb in callbacks:
            self.callbacks[hook].append(cb)

    def add_end_callback(self, callback):
        self.add_callback(ON_TRANSITION_END, callback)

    def pass_time(self, time_passed):
        extra_time = self.do_transition(time_passed)
        if self.iscomplete():
            for callback in self.callbacks[ON_ANIMATION_END]:
                try:
                    callback(extra_time)
                except Exception as e:
                    LOG.exception("Failed to run callback {}:{}".format(callback, e))

    def do_transition(self, time_passed):
        raise NotImplementedError()

    def iscomplete(self):
        raise NotImplementedError()

    def start(self, extra_time=timedelta(0)):
        pass


class StaticDelay(TransitionEngine):

    def __init__(self, sprite, duration=0.0, **kwargs):
        super(StaticDelay, self).__init__(sprite, **kwargs)
        self.duration = duration
        self.delay_remaining = self.duration and timedelta(seconds=self.duration) or False

    def iscomplete(self):
        return not self.delay_remaining

    def do_transition(self, time_passed):
        if self.delay_remaining:
            self.delay_remaining -= time_passed
            if self.delay_remaining < timedelta(0.0):
                self.delay_remaining = False
                return -self.delay_remaining


class MoveEngine(TransitionEngine):

    def __init__(self, sprite, destination, speed, **kwargs):
        super(MoveEngine, self).__init__(sprite, **kwargs)
        self.destination = destination
        self.speed = speed
        self.calc_unit_vector
        self.complete = False
        self.calc_unit_vector()

    def calc_unit_vector(self):
        from_x, from_y = self.sprite.x, self.sprite.y
        dest_x, dest_y = self.destination
        a = dest_x - from_x
        b = dest_y - from_y
        c = (a**2 + b**2)**0.5
        self.unit_x, self.unit_y = (a/c, b/c)

    def do_transition(self, time_passed):
        extra_time = timedelta(0)
        x_diff = time_passed.total_seconds() * self.speed * self.unit_x
        y_diff = time_passed.total_seconds() * self.speed * self.unit_y
        dest_x, dest_y = self.destination
        x_to_go = abs(dest_x - self.sprite.x)
        y_to_go = abs(dest_y - self.sprite.y)
        x_diff_mag = abs(x_diff)
        y_diff_mag = abs(y_diff)
        x_overshoot = x_diff_mag - x_to_go
        y_overshoot = y_diff_mag - y_to_go
        overshoot = False
        if self.unit_x and x_overshoot >= 0:
            extra_time = time_passed.total_seconds() * x_overshoot / x_diff
            overshoot = True
        if self.unit_y and y_overshoot >= 0:
            extra_time = time_passed.total_seconds() * y_overshoot / y_diff
            overshoot = True
        if overshoot:
            self.complete = True
            self.sprite.x, self.sprite.y = self.destination
        else:
            self.sprite.x, self.sprite.y = self.sprite.x + x_diff, self.sprite.y + y_diff
        return extra_time

    def iscomplete(self):
        return self.complete


class MoveWithAnimationEngine(MoveEngine):

    def __init__(self, sprite, destination, speed, animation, resting_component=None, **kwargs):
        super(MoveWithAnimationEngine, self).__init__(sprite, destination, speed, **kwargs)
        self.animation = animation
        self.add_end_callback(self.stop_animation)
        self.resting_component = resting_component

    def start(self, extra_time=timedelta(0)):
        self.restart_animation(extra_time)

    def restart_animation(self, extra_time=timedelta(0)):
        self.sprite.start_animation(
            self.animation, extra_time=extra_time, end_callback=self.restart_animation
        )

    def stop_animation(self, extra_time):
        self.sprite.stop_animation(run_callbacks=False)
        if self.resting_component:
            self.sprite.set_component(self.resting_component)


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
            self.true_center_y = self.height / 2

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

    def get_duration(self):
        duration = 0.0
        for stage in self.stages:
            duration += stage.duration
            return duration

    def __getstate__(self):
        state = super(AscAnimation, self).__getstate__()
        state["anchor"] = getattr(self, "anchor", "center")
        return state

    def __setstate__(self, state):
        super(AscAnimation, self).__setstate__(state)
        self.anchor = state.get("anchor", "center")
        for stage in self.stages:
            stage.anchor = self.anchor


class AscAnimationPlayer(SpriteAnimationPlayer):

    def start(self, extra_time=timedelta(0)):
        self.start_animation(extra_time=extra_time)

    def pass_time(self, time_passed):
        self.pass_animation_time(time_passed)


def sprite_cmp(sprite, other):
    funcs = [lambda x: -x.z, lambda x: -x.y, lambda x: id(x)]
    for func in funcs:
        this_value = func(sprite)
        other_value = func(other)
        if this_value < other_value:
            return -1
        elif this_value > other_value:
            return 1
    return 0


class RemoveEngineCallback(object):

    def __init__(self, sprite, engine):
        self.sprite = sprite
        self.engine = engine

    def __call__(self, extra_time):
        if self.engine not in self.sprite.transition_engines:
            raise KeyError(
                "Unable to find engine {} in sprite {}".format(self.engine, self.sprite)
            )
        self.sprite.transition_engines.remove(self.engine)


class Sprite(object):

    def __init__(self, x=0, y=0, z=0, component_name=None, anchor="center",
                 behind_subsprites=[], infront_subsprites=[]):
        self.x = floor(x)
        self.y = floor(y)
        self.z = z
        self.component = None
        self.visible = True
        self.transition_engines = []
        self.animation_player = None
        self.animation = None
        self.displacement_x = 0
        self.displacement_y = 0
        self.anchor = anchor
        self.subsprites = {}
        self.behind_subsprites = behind_subsprites
        self.infront_subsprites = infront_subsprites
        self.texture = SpriteManager.texture
        self.texture_width = float(self.texture.width)
        self.texture_height = float(self.texture.height)
        if component_name:
            self.set_component(component_name, anchor=anchor)

    __cmp__ = sprite_cmp

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
                      duration=None, anchor=None):
        if not component:
            if not component_name:
                raise ValueError("set_component requires either a component or a component name")
            component = SpriteManager.get_component(component_name)
        self.component = component
        self.compoennt_name = component_name or component.name
        self.duration = duration
        self.anchor = anchor or self.anchor
        self.anchor_x, self.anchor_y = self.component.get_anchor(self.anchor)
        self.displacement_x = displacement_x
        self.displacement_y = displacement_y
        self.component_x_ratio = self.component_x / self.texture_width
        self.component_y_ratio = self.component_y / self.texture_height
        self.relative_component_width = self.component_width / self.texture_width
        self.relative_component_height = self.component_height / self.texture_height

    def get_component_center(self):
        return self.component_width / 2, self.component_height

    def draw(self, offset, scale):
        subsprite_offset = (offset[0] + self.x, offset[1] + self.y)
        for subsprite in self.behind_subsprites:
            subsprite.draw(subsprite_offset, scale)
        try:
            if not self.component or not self.visible:
                return
            width = self.component_width * scale
            height = self.component_height * scale
            offset_x, offset_y = offset
            draw_x = (
                (self.x + self.displacement_x - self.anchor_x + offset_x) * scale
            )
            draw_y = (
                (self.y + self.displacement_y - self.component_height + self.anchor_y + offset_y) * scale
            )
            draw_z = 0.0
            array = (gl.GLfloat * 32)(
                self.component_x_ratio, self.component_y_ratio, 0.0, 1.,
                draw_x, draw_y, draw_z, 1.,
                self.component_x_ratio + self.relative_component_width, self.component_y_ratio, 0.0, 1.,
                draw_x + width, draw_y, draw_z, 1.,
                self.component_x_ratio + self.relative_component_width,
                    self.component_y_ratio + self.relative_component_height, 0.0, 1.,
                draw_x + width, draw_y + height, draw_z, 1.,
                self.component_x_ratio, self.component_y_ratio + self.relative_component_height, 0.0, 1.,
                draw_x, draw_y + height, draw_z, 1.
            )
            ProfilerManager.start("GL_DRAW_ARRAYS")
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
            gl.glPushClientAttrib(gl.GL_CLIENT_VERTEX_ARRAY_BIT)
            gl.glInterleavedArrays(gl.GL_T4F_V4F, 0, array)
            gl.glDrawArrays(gl.GL_QUADS, 0, 4)
            gl.glPopClientAttrib()
            ProfilerManager.stop("GL_DRAW_ARRAYS")
        except Exception:
            LOG.exception("Exception encountered drawing sprite {}".format(self))
        for subsprite in self.infront_subsprites:
            subsprite.draw(subsprite_offset, scale)

    def tick(self, time_passed):
        for subsprite in self.infront_subsprites + self.behind_subsprites:
            subsprite.tick(time_passed)
        engines = [eng for eng in self.transition_engines]
        for engine in engines:
            if engine in self.transition_engines:
                try:
                    engine.pass_time(timedelta(seconds=time_passed))
                except Exception:
                    LOG.exception("Exception encountered in pass_time of engine {}".format(engine))

    def start_animation(self, animation, override=False, **kwargs):
        if self.animation_player and not self.animation_player.iscomplete():
            if override:
                self.transition_engines.remove(self.animation_player)
            else:
                raise Exception("{0} set to animation {1} while already in animation {2}".format(
                    self, animation, self.animation
                ))
        self.animation = animation
        self.animation_player = AscAnimationPlayer(self, self.animation)
        self.animation_player.add_end_callback(self.clear_complete_animation)
        self.add_transition_engine(self.animation_player, **kwargs)

    def static_delay(self, duration, **kwargs):
        self.add_transition_engine(StaticDelay(self, duration=duration), **kwargs)

    def move_to(self, destination, speed, animation=None, resting_component=None, **kwargs):
        if animation:
            move_engine = MoveWithAnimationEngine(
                self, destination, speed, animation, resting_component=resting_component,
            )
        else:
            move_engine = MoveEngine(self, destination, speed)
        self.add_transition_engine(move_engine, **kwargs)

    def add_transition_engine(self, engine, extra_time=0, end_callback=None, callbacks={}):
        self.transition_engines.append(engine)
        for hook, callback_list in callbacks.items():
            for callback in callback_list:
                engine.add_callback(hook, callback)
        if end_callback:
            if not isinstance(end_callback, (tuple, list)):
                end_callback = [end_callback]
            for callback in end_callback:
                engine.add_end_callback(callback)
        engine.add_end_callback(RemoveEngineCallback(self, engine))
        engine.start(extra_time=timedelta(0))

    def stop_animation(self, run_callbacks=False, error_on_no_animation=True):
        if self.animation_player:
            self.transition_engines.remove(self.animation_player)
            if not self.animation_player.iscomplete() and run_callbacks:
                self.animation_player.run_hook(ON_TRANSITION_END)
            self.clear_complete_animation()
        elif error_on_no_animation:
            raise KeyError("Sprite {} has no animation to stop".format(self))

    def clear_complete_animation(self, extra_time=timedelta(0)):
        self.animation_player = None
        self.animation = None

    def add_subsprite(self, subsprite, infront=True):
        if infront:
            self.infront_subsprites.append(subsprite)
        else:
            self.behind_subsprites.append(subsprite)


class TextSprite(object):

    def __init__(self, x=0, y=0, z=0, text=None, font_name="Times New Roman", font_size=20,
                 anchor_x="center", anchor_y="center"):
        self.set_position(x, y)
        self.set_text(
            text, font_name=font_name, font_size=font_size, anchor_x=anchor_x, anchor_y=anchor_y
        )

    __cmp__ = sprite_cmp

    def set_position(self, x, y):
        for key, value in ("x", x), ("y", y):
            try:
                setattr(self, key, floor(value))
            except TypeError:
                setattr(self, key, value)

    def set_text(self, text, font_size=None, font_name=None, anchor_x=None, anchor_y=None):
        self.text = text
        self.font_size = font_size or self.font_size
        self.font_name = font_name or self.font_name
        self.anchor_x = anchor_x or self.anchor_x
        self.anchor_y = anchor_y or self.anchor_y
        if self.text:
            self.label = Label(
                text, x=self.x, y=self.y, font_size=self.font_size, font_name=self.font_name,
                anchor_x=self.anchor_x, anchor_y=self.anchor_y
            )
        else:
            self.label = None

    def tick(self, time_passed):
        pass

    def draw(self, offset, scale):
        self.label.x = (self.x + offset[0]) * scale
        self.label.y = (self.y + offset[1]) * scale
        self.label.draw()


class SpriteGroup(object):

    def __init__(self, groupnum, keep_sorted=True, gl_texture=True, active=True):
        self.groupnum = groupnum
        self.keep_sorted = keep_sorted
        self.sprites = []
        self.active = active
        self.gl_texture = gl_texture

    def update(self):
        if self.active and self.keep_sorted:
            self.sort()

    def add_sprite(self, sprite):
        self.sprites.append(sprite)

    def remove_sprite(self, sprite):
        self.sprites.remove(sprite)

    def sort(self):
        insert_sort(self.sprites)

    def draw(self, offset, scale):
        if self.active:
            spritelist = self.sprites
            for sprite in spritelist:
                sprite.draw(offset, scale)

    def tick(self, time_passed):
        if self.active:
            for sprite in self.sprites:
                sprite.tick(time_passed)


class SpriteManager(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.load_atlas()
        self.sprites = {}
        self.sprite_groups = {}
        self.sprite_group_nums = []
        self.scale = 2.0
        self.first = True
        self.add_sprite_group(TILE_GROUP, keep_sorted=False)
        self.add_sprite_group(UNIT_GROUP, keep_sorted=True)
        self.add_sprite_group(OVERLAY_GROUP, keep_sorted=False, gl_texture=False)
        self.gl_texture_enabled = False

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

    def _enable_gl_texture(self):
        gl.glEnable(self.texture.target)
        gl.glBindTexture(self.texture.target, self.texture.id)
        self.gl_texture_enabled = True

    def _disable_gl_texture(self):
        gl.glDisable(self.texture.target)
        self.gl_texture_enabled = False

    def set_gl_texture(self, enabled):
        if self.gl_texture_enabled and not enabled:
            self._disable_gl_texture()
        elif not self.gl_texture_enabled and enabled:
            self._enable_gl_texture()

    def get_component(self, component_name):
        return self.components[component_name]

    def add_sprite_group(self, groupnum, *args, **kwargs):
        if groupnum in self.sprite_group_nums:
            raise KeyError(
                "Sprite Group number '{}' is already registered with the SpriteManager"
                .format(groupnum)
            )
        group = SpriteGroup(groupnum, *args, **kwargs)
        self.sprite_groups[groupnum] = group
        self.sprite_group_nums.append(groupnum)
        self.sprite_group_nums.sort()

    def add_sprite(self, group, sprite):
        self.sprites[sprite] = group
        self.sprite_groups[group].add_sprite(sprite)

    def remove_sprite(self, sprite):
        group = self.sprites[sprite]
        self.sprite_groups[group].remove_sprite(sprite)

    def draw_sprites(self, offset):
        offset = [x / self.scale for x in offset]
        self.update_sprite_groups()
        ProfilerManager.start("DRAW_SPRITES")
        for groupnum in self.sprite_group_nums:
            group = self.sprite_groups[groupnum]
            self.draw_group(offset, group)
        ProfilerManager.stop("DRAW_SPRITES")
        self.set_gl_texture(False)

    def draw_group(self, offset, group):
        self.set_gl_texture(group.gl_texture)
        group.draw(offset, self.scale)

    def tick(self, time_passed):
        for sprite_group in self.sprite_groups.values():
            sprite_group.tick(time_passed)

    def update_sprite_groups(self):
        ProfilerManager.start("SORT_SPRITES")
        for sprite_group in self.sprite_groups.values():
            sprite_group.update()
        ProfilerManager.stop("SORT_SPRITES")

    def set_group_active(self, groupnum, active=True):
        group = self.sprite_groups[groupnum]
        group.active = active

    def get_group_active(self, groupnum):
        group = self.sprite_groups[groupnum]
        return group.active

    def toggle_group_active(self, groupnum):
        group = self.sprite_groups[groupnum]
        group.active = not group.active

    def get_adjusted_position(self, x, y, offset):
        x = ceil((x - offset[0]) / self.scale)
        y = ceil((y - offset[1]) / self.scale)
        return x, y

    def get_animation(self, animation):
        return self.animations[animation]

