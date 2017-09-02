import pyglet
import logging
import yaml
import math
from datetime import timedelta
from math import floor, ceil
import os

from pyglet.text import Label
from sprite.component import SpriteComponent
from sprite.animation import (
    SpriteAnimation, SpriteAnimationStage, ON_ANIMATION_END
)

from ascension.util import Singleton
from ascension.settings import AscensionConf as conf

LOG = logging.getLogger(__name__)


SEA_GROUP = 1
TILE_GROUP = 0
TILE_OVERLAY_GROUP = -1
UNIT_GROUP = -10
SHROUD_GROUP = -15
OVERLAY_GROUP = -20
ON_TRANSITION_END = ON_ANIMATION_END


class TransitionEngine(object):

    def __init__(self, sprite, delete_after=False, end_callback=None, callbacks={}):
        self.delete_after = delete_after
        self.sprite = sprite
        for hook, callback_list in callbacks.items():
            for callback in callback_list:
                self.add_callback(hook, callback)
        if end_callback:
            if not isinstance(end_callback, (tuple, list)):
                end_callback = [end_callback]
            for callback in end_callback:
                self.add_end_callback(callback)
        if delete_after:
            self.add_end_callback(sprite.delete)
        self.add_end_callback(RemoveEngineCallback(self.sprite, self))


    def add_callback(self, hook, callback):
        if not hasattr(self, "callbacks"):
            self.callbacks = {}
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
        if extra_time:
            self.do_transition(extra_time)


class StaticDelay(TransitionEngine):

    def __init__(self, sprite, duration=0, **kwargs):
        super(StaticDelay, self).__init__(sprite, **kwargs)
        self.duration = float(duration)
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
            self.sprite.set_position(*self.destination)
        else:
            self.sprite.set_position(self.sprite.x + x_diff, self.sprite.y + y_diff)
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


class FadeEngine(TransitionEngine):

    def __init__(self, sprite, start_alpha=None, finish_alpha=0, duration=0,
                 **kwargs):
        super(FadeEngine, self).__init__(sprite, **kwargs)
        self.start_alpha = start_alpha
        self.finish_alpha = finish_alpha
        self.duration = float(duration)

    def start(self, extra_time=timedelta(0)):
        if self.duration == 0:
            self.sprite.set_opacity(self.finish_alpha)
            return
        if not self.start_alpha:
            self.start_alpha = self.sprite.opacity
        else:
            self.sprite.set_opacity(self.start_alpha)
        self.continuous_alpha = float(self.start_alpha)
        self.alpha_diff = self.finish_alpha - self.start_alpha
        self.direction = self.alpha_diff > 0 and 1 or -1
        self.time_alpha_ratio = self.alpha_diff / float(self.duration)
        super(FadeEngine, self).start(extra_time=extra_time)

    def do_transition(self, time_passed):
        opacity_change = time_passed.total_seconds() * self.alpha_diff
        self.continuous_alpha += opacity_change
        left = self.finish_alpha - self.continuous_alpha
        if left * self.direction <= 0:
            self.sprite.set_opacity(self.finish_alpha)
        else:
            self.sprite.set_opacity(math.floor(self.continuous_alpha))

    def iscomplete(self):
        return self.sprite.opacity == self.finish_alpha


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


class AscAnimationPlayer(TransitionEngine):

    def __init__(self, sprite, animation, **kwargs):
        self.add_end_callback(sprite.clear_complete_animation)
        super(AscAnimationPlayer, self).__init__(sprite, **kwargs)
        self.animation = animation
        self.stage_index = 0

    def start(self, extra_time=timedelta(0)):
        self.stage_index = 0
        self.start_next_stage()
        super(AscAnimationPlayer, self).start(extra_time=extra_time)

    def start_next_stage(self, extra_time=timedelta(0)):
        try:
            self.stage = self.animation.stages[self.stage_index]
        except IndexError:
            return extra_time
        self.stage.update_renderer(self.sprite)
        self.stage_time_remaining = timedelta(seconds=self.stage.duration)
        return self.do_transition(extra_time)

    def do_transition(self, time_passed):
        self.stage_time_remaining -= time_passed
        if self.stage_time_remaining <= timedelta():
            self.stage_index += 1
            return self.start_next_stage(extra_time=-self.stage_time_remaining)

    def iscomplete(self):
        return self.stage_index == len(self.animation.stages)


class RemoveEngineCallback(object):

    def __init__(self, sprite, engine):
        self.sprite = sprite
        self.engine = engine

    def __call__(self, extra_time):
        if self.engine in self.sprite.transition_engines:
            self.sprite.transition_engines.remove(self.engine)


class Callback(object):

    def __init__(self, function, *args, **kwargs):
        self.function = function
        self.args = args
        self.kwargs = kwargs
        circular = kwargs.pop("circular_callback", False)
        if circular:
            if "end_callback" in kwargs:
                end_callback = kwargs["end_callback"]
                if not isinstance(end_callback, (tuple, list)):
                    end_callback = [end_callback]
            else:
                end_callback = []
            end_callback.append(self)
            kwargs["end_callback"] = end_callback


    def __call__(self, extra_time):
        self.function(*self.args, extra_time=extra_time, **self.kwargs)


def transition_engine(func):
    def new_func(self, *args, **kwargs):
        static_delay = kwargs.pop("static_delay", 0)
        extra_time = kwargs.pop("extra_time", timedelta(0))
        if static_delay:
            callback = Callback(new_func, self, *args, **kwargs)
            self.static_delay(static_delay, extra_time=extra_time, end_callback=callback)
        else:
            engine = func(self, *args, **kwargs)
            self.transition_engines.append(engine)
            engine.start(extra_time=extra_time)
    return new_func


class BaseSprite(object):

    def __init__(self, component_name=None, anchor="center"):
        self.component = None
        self.transition_engines = []
        self.animation_player = None
        self.animation = None
        self.displacement_x = 0
        self.displacement_y = 0
        self.anchor = anchor
        self.deleted = False
        self.xyz_updated = True
        if component_name:
            self.set_component(component_name, anchor=anchor)

    def delete(self, extra_time=timedelta(0)):
        self.deleted = True
        self.transition_engines = []
        self.animation_player = None
        self.animation = None
        SpriteManager.remove_sprite(self)

    def __unicode__(self):
        return "{classname}(x={x}, y={y}, {component})".format(
            classname=type(self).__name__, component=self.component_name, x=self.x, y=self.y
        )

    def __str__(self):
        return unicode(self)

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

    def add_subsprite(self, subsprite):
        self.subsprites.append(subsprite)

    def get_relative_pyglet_xy(self):
        if self.xyz_updated:
            self.rel_x = (
                (self.displacement_x - self.anchor_x)
            )
            self.rel_y = (
                (self.displacement_y - self.component_height + self.anchor_y)
            )
        return self.rel_x, self.rel_y

    def get_component_center(self):
        return self.component_width / 2, self.component_height

    def tick(self, time_passed):
        engines = [eng for eng in self.transition_engines]
        for engine in engines:
            if engine in self.transition_engines:
                try:
                    engine.pass_time(timedelta(seconds=time_passed))
                except Exception:
                    LOG.exception(
                        "Exception encountered in pass_time of engine {}".format(engine)
                    )

    @transition_engine
    def start_animation(self, animation, override=False, **kwargs):
        if self.animation_player and not self.animation_player.iscomplete():
            if override:
                self.transition_engines.remove(self.animation_player)
            else:
                raise Exception("{0} set to animation {1} while already in animation {2}".format(
                    self, animation, self.animation
                ))
        if not isinstance(animation, AscAnimation):
            animation = SpriteManager.get_animation(animation)
        self.animation = animation
        self.animation_player = AscAnimationPlayer(self, self.animation, **kwargs)
        return self.animation_player

    @transition_engine
    def static_delay(self, duration, **kwargs):
        engine = StaticDelay(self, duration, **kwargs)
        return engine

    @transition_engine
    def move_to(self, destination, speed, **kwargs):
        if "animation" in kwargs and kwargs["animation"]:
            move_engine = MoveWithAnimationEngine(
                self, destination, speed, **kwargs
            )
        else:
            kwargs.pop("resting_component", None)
            move_engine = MoveEngine(self, destination, speed, **kwargs)
        return move_engine

    @transition_engine
    def fade(self, *args, **kwargs):
        fade = FadeEngine(self, *args, **kwargs)
        return fade

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


class SpriteMaster(BaseSprite):

    def __init__(self, **kwargs):
        self.sprite_followers = []
        super(SpriteMaster, self).__init__(**kwargs)

    def delete(self, extra_time=timedelta(0)):
        super(SpriteMaster, self).delete(extra_time=extra_time)
        for follower in list(self.sprite_followers):
            follower.delete()

    def add_follower(self, follower):
        if follower in self.sprite_followers:
            raise KeyError("{} already has follower {}".format(self, follower))
        self.set_follower_component(follower)
        self.sprite_followers.append(follower)

    def remove_follower(self, follower):
        if follower not in self.sprite_followers:
            raise KeyError(
                "{} cannot remove follower {} because it doesn't have it".format(self, follower)
            )
        self.sprite_followers.remove(follower)

    def set_component(self, component_name=None, component=None, displacement_x=0,
                      displacement_y=0, duration=None, anchor=None):
        if self.deleted:
            return
        if not component:
            if not component_name:
                raise ValueError("set_component requires either a component or a component name")
            component = SpriteManager.get_component(component_name)
        self.component = component
        self.image = SpriteManager.get_component_image(component.name)
        self.duration = duration
        self.anchor = anchor or self.anchor
        self.anchor_x, self.anchor_y = self.component.get_anchor(self.anchor)
        self.displacement_x = displacement_x
        self.displacement_y = displacement_y
        for follower in self.sprite_followers:
            self.set_follower_component(follower)

    def set_follower_component(self, follower):
        follower.set_component(
            component=self.component, displacement_x=self.displacement_x,
            displacement_y=self.displacement_y, duration=self.duration,
            anchor=self.anchor
        )



class Sprite(BaseSprite):

    def __init__(self, x=0, y=0, z_group=0, parent=None, master=None, opacity=255, **kwargs):
        self.x = floor(x)
        self.y = floor(y)
        self.z_group = z_group
        self.pyglet_sprite = None
        self.visible = True
        self.parent = parent
        self.set_opacity(opacity)
        if parent:
            parent.add_subsprite(self)
        self.subsprites = []

        super(Sprite, self).__init__(**kwargs)

        self.master = None
        if master:
            self.set_master(master)

    def delete(self, extra_time=timedelta(0)):
        super(Sprite, self).delete(extra_time=extra_time)
        for subsprite in self.subsprites:
            subsprite.delete()
        self.subsprites = []
        if self.pyglet_sprite:
            self.pyglet_sprite.delete()
            self.pyglet_sprite = None
        if self.master:
            self.master.remove_follower(self)

    def tick(self, time_passed):
        super(Sprite, self).tick(time_passed)
        if self.xyz_updated:
            self.update_pyglet_xy()
            self.xyz_updated = False

    def set_position(self, x, y):
        self.x = x
        self.y = y
        self.xyz_updated = True

    def set_master(self, master):
        master.add_follower(self)
        self.master = master

    def set_opacity(self, opacity):
        self.opacity = opacity
        if self.pyglet_sprite:
            self.pyglet_sprite.opacity = opacity

    def get_pyglet_xyz(self):
        rel_x, rel_y = self.get_relative_pyglet_xy()
        asc_x = self.x + rel_x
        asc_y = self.y + rel_y
        if self.parent:
            asc_x += self.parent.x
            asc_y += self.parent.y
        draw_x = asc_x * conf.sprite_scale
        draw_y = asc_y * conf.sprite_scale
        draw_z = self.get_pyglet_z(asc_x, asc_y)
        return draw_x, draw_y, draw_z

    def set_component(self, component_name=None, component=None, displacement_x=0,
                      displacement_y=0, duration=None, anchor=None):
        if self.deleted:
            return
        if not component:
            if not component_name:
                raise ValueError("set_component requires either a component or a component name")
            component = SpriteManager.get_component(component_name)
        self.component = component
        self.image = SpriteManager.get_component_image(component.name)
        self.duration = duration
        self.anchor = anchor or self.anchor
        self.anchor_x, self.anchor_y = self.component.get_anchor(self.anchor)
        self.displacement_x = displacement_x
        self.displacement_y = displacement_y
        if not self.pyglet_sprite:
            draw_x, draw_y, draw_z = self.get_pyglet_xyz()
            self.initialize_pyglet_sprite(
                image=self.image, draw_x=draw_x, draw_y=draw_y, draw_z=draw_z,
            )
        else:
            self.pyglet_sprite.image = self.image
        self.xyz_updated = True

    def initialize_pyglet_sprite(self, image, draw_x, draw_y, draw_z):
        self.pyglet_sprite = pyglet.sprite.Sprite(
            self.image, x=draw_x, y=draw_y, order=draw_z, batch=SpriteManager.batch,
        )
        self.pyglet_sprite.opacity = self.opacity

    def update_pyglet_xy(self):
        if self.deleted:
            return
        draw_x, draw_y, draw_z = self.get_pyglet_xyz()
        if draw_x != self.pyglet_sprite.x or draw_y != self.pyglet_sprite.y:
            self.pyglet_sprite.x = draw_x
            self.pyglet_sprite.y = draw_y
            self.pyglet_sprite.order = draw_z
        for subsprite in self.subsprites:
            subsprite.update_pyglet_xy()

    def get_pyglet_z(self, x, y):
        return self.z_group + 0.001 * y + 0.00001 * x


class TextSprite(object):

    def __init__(self, x=0, y=0, z=0, text=None, font_name="Times New Roman", font_size=20,
                 anchor_x="center", anchor_y="center"):
        self.set_position(x, y)
        self.set_text(
            text, font_name=font_name, font_size=font_size, anchor_x=anchor_x, anchor_y=anchor_y
        )

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
        self.label.x = (self.x) * scale
        self.label.y = (self.y + offset[1]) * scale
        self.label.draw()


class SpriteManager(object):
    __metaclass__ = Singleton

    def __init__(self):
        self.load_atlas()
        self.sprites = []
        self.batch = pyglet.graphics.Batch()

    def load_atlas(self):
        self.component_images = {}
        with open(conf.atlas_meta) as f:
            atlas_data = yaml.load(f)
        self.atlas = pyglet.image.atlas.TextureAtlas(4096, 4096)
        self.components = {}
        for component_data in atlas_data["components"]:
            component = AscSpriteComponent.from_meta(component_data)
            self.components[component.name] = component
            image_name = "{}.png".format(component.name)
            image_path = os.path.join(conf.img_dir, image_name)
            image = pyglet.image.load(image_path)
            texture_region = self.atlas.add(image)
            self.component_images[component.name] = texture_region
        self.animations = {}
        for animation_data in atlas_data["animations"]:
            animation = AscAnimation.load(animation_data)
            for stage in animation.stages:
                stage.component = self.components[stage.component_name]
            self.animations[animation.name] = animation

    def get_component(self, component_name):
        return self.components[component_name]

    def add_sprite(self, sprite):
        self.sprites.append(sprite)
        if hasattr(sprite, "subsprites"):
            for subsprite in sprite.subsprites:
                self.add_sprite(subsprite)

    def remove_sprite(self, sprite):
        for subsprite in sprite.subsprites:
            self.remove_sprite(subsprite)
        self.sprites.remove(sprite)

    def draw_sprites(self, offset):
        self.batch.draw()

    def tick(self, time_passed):
        for sprite in self.sprites:
            try:
                sprite.tick(time_passed)
            except Exception as e:
                LOG.exception("Failed to tick sprite {}:{}".format(sprite, e))

    def get_adjusted_position(self, x, y, offset):
        x = ceil((x - offset[0]) / conf.sprite_scale)
        y = ceil((y - offset[1]) / conf.sprite_scale)
        return x, y

    def get_animation(self, animation):
        return self.animations[animation]

    def get_component_image(self, component_name):
        return self.component_images[component_name]
