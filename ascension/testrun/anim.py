from ascension.game import Ascension
from ascension.window import MainWindowManager
from ascension.ascsprite import SpriteManager, Sprite, UNIT_GROUP
from math import ceil, floor
from ascension.settings import AscensionConf as conf


BUFFER = (20, 20)


class RepeatCallback(object):

    def __init__(self, sprite, animation):
        self.sprite = sprite
        self.animation = animation

    def __call__(self, extra_time):
        self.sprite.start_animation(self.animation, extra_time, end_callback=self)


class AnimTest(Ascension):

    def initialize(self, *animation_names):
        MainWindowManager.set_background_color(0.5, 0.5, 0.5)
        self.animation_names = animation_names
        self.animation_sprites = []
        if self.animation_names and animation_names[0] == "list":
            self.list_animations()
            import sys
            sys.exit(0)
        else:
            self.find_animations()
            self.determine_cell_size()
            self.add_sprites()

    def list_animations(self):
        animations = [a.name for a in SpriteManager.animations.values()]
        animations.sort()
        for animation in animations:
            print animation

    def find_animations(self):
        self.animations = []

        for animation in SpriteManager.animations.values():
            if not self.animation_names or animation.name in self.animation_names:
                self.animations.append(animation)
        self.animations.sort(key=lambda x: x.name)

    def determine_cell_size(self):
        max_width = 0
        max_height = 0
        for animation in self.animations:
            max_width = max(max_width, animation.width)
            max_height = max(max_height, animation.height)
        self.cell_width = max_width + BUFFER[0] * 2.0
        self.cell_height = max_height + BUFFER[1] * 2.0

    def add_sprites(self):
        window_width = MainWindowManager.width / conf.sprite_scale
        window_height = MainWindowManager.height / conf.sprite_scale
        start_x = ceil((-window_width + self.cell_width) / 2)
        x = start_x
        y = floor((window_height - self.cell_height) / 2)
        for animation in self.animations:
            self.add_sprite(animation, x, y)
            x += self.cell_width
            if x + self.cell_width / 2 > window_width / 2:
                x = start_x
                y -= self.cell_height

    def add_sprite(self, animation, x, y):
        newsprite = Sprite(x=x, y=y)
        newsprite.start_animation(animation, end_callback=RepeatCallback(newsprite, animation))
        SpriteManager.add_sprite(newsprite)
