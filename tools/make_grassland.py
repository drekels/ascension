import os
import yaml
import signal
import time
from threading import Thread
from decimal import Decimal, getcontext

from sortedcontainers import SortedList
from PIL import Image

from ascension.perlin import TileablePerlinGenerator
from ascension.settings import AscensionConf as conf
from tools.util import (
    is_in_hex, print_progress_bar, get_topleft_tile_point, clear_dir
)


color_map = [
    (Decimal('0.2'), (2, 5, 74)),
    (Decimal('0.2'), (2, 4, 82)),
    (Decimal('0.4'), (2, 2, 90)),
    (Decimal('0.1'), (3, 5, 115)),
    (Decimal('0.1'), (3, 8, 140)),
]


class FrameGenerator(object):

    def __init__(self, color_map, perlin_generators, width, height, z):
        self.color_map = list(color_map)
        self.perlin_generators = perlin_generators
        self.image = None
        self.z = z
        self.point_list = SortedList()
        self.width = width
        self.height = height
        self.pixels_calculated = 0
        self.total_pixels = Decimal(self.width * self.height)
        self.error = None

    def find_value(self, x, y):
        value = Decimal('0.0')
        perlin_x = Decimal(x) / self.width
        perlin_y = Decimal(y) / self.height
        for generator in self.perlin_generators:
            args = (perlin_x, perlin_y)
            if len(generator.dimensions) == 3:
                args = (perlin_x, perlin_y, self.z)
            v = generator.get_value(*args)
            value += v * generator.weight
        self.point_list.add((value, (x, y)))
        self.pixels_calculated += 1

    def find_values(self):
        for i in range(self.width):
            for j in range(self.height):
                if self.error:
                    return
                self.find_value(i, j)

    def draw_image(self):
        self.image = Image.new('RGB', (self.width, self.height))
        self.pixels = self.image.load()
        threshhold, color = self.color_map.pop()
        for i in range(len(self.point_list)):
            x, y = self.point_list[-(i+1)][1]
            self.pixels[x, y] = color
            if (i+1) / self.total_pixels > threshhold:
                new_threshhold, color = self.color_map.pop()
                threshhold += new_threshhold

    def get_frame(self):
        if not self.image:
            self.find_values()
            self.draw_image()
        return self.image, self.pixels


class GrasslandGenerator(object):
    perlin_setup = [
        {"weight": Decimal('0.7'), "dimensions": (8, 50), "seed": 32},
        {"weight": Decimal('0.3'), "dimensions": (8, 50, 2), "seed": 1},
    ]
    decimal_precision = 5
    animation_frame_count = 10
    animation_duration = 2
    group_name = "sea"
    hex_count_horz = 2
    hex_count_vert = 2
    hex_horz_point_width = 15
    hex_center_width = 41
    hex_height = 30
    outdir = os.getcwd()
    animation_meta_filename = "meta.yaml"
    progress_bar_sleep = 5

    @classmethod
    def make_sea(cls, **kwargs):
        obj = cls(**kwargs)
        obj.start()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        getcontext().prec = self.decimal_precision
        self.perlin_generators = []
        for spec in self.perlin_setup:
            generator = TileablePerlinGenerator(**spec)
            self.perlin_generators.append(generator)
        self.pixel_count = conf.frame_pixel_count * self.animation_frame_count
        self.animation_duration = Decimal(self.animation_duration)
        self.frame_duration = self.animation_duration / self.animation_frame_count
        self.error = None
        self.frame_generators = []

    def start(self):
        try:
            signal.signal(signal.SIGINT, self.handle_sigint)
            self.create_dir()
            self.make_images()
            self.make_animations()
            self.wait_for_finish()
        except Exception as e:
            self.error = e
            raise
        finally:
            if self.error:
                for generator in self.frame_generators:
                    generator.error = self.error

    def create_dir(self):
        self.imgdir = os.path.join(self.outdir, self.group_name)
        clear_dir(self.imgdir)

    def make_images(self):
        self.threads = []
        for framenum in range(self.animation_frame_count):
            thread = Thread(target=self.try_make_frame, args=(framenum,))
            self.threads.append(thread)
            thread.start()

    def threads_running(self):
        return sum([thread.isAlive() for thread in self.threads])

    def make_animations(self):
        self.meta = {"animations": []}
        for hexnum in range(conf.frame_tile_count_vert * conf.frame_tile_count_horz):
            stages = []
            for framenum in range(self.animation_frame_count):
                component_name = self.get_hex_name(framenum, hexnum)
                stages.append({
                    "component_name": component_name,
                    "duration": float(self.frame_duration),
                })
            animation = {
                "name": "{}_{}".format(self.group_name, hexnum),
                "stages": stages
            }
            self.meta["animations"].append(animation)
        filepath = os.path.join(self.imgdir, self.animation_meta_filename)
        with open(filepath, "w") as f:
            f.write(yaml.dump(self.meta))

    def try_make_frame(self, framenum):
        try:
            self.make_frame(framenum)
        except Exception as e:
            self.error = e
            raise

    def make_frame(self, framenum):
        z = Decimal(framenum) / self.animation_frame_count
        frame_generator = FrameGenerator(
            z=z, perlin_generators=self.perlin_generators, color_map=color_map,
            width=conf.frame_width, height=conf.frame_height,
        )
        self.frame_generators.append(frame_generator)
        frame_image, frame_pixels = frame_generator.get_frame()
        self.make_hexes(framenum, frame_pixels)
        frame_image.save(os.path.join(self.imgdir, "{}_{}.png".format(self.group_name, framenum)))

    def make_hexes(self, framenum, frame_pixels):
        hexnum = 0
        for i in range(conf.frame_tile_count_horz):
            for j in range(conf.frame_tile_count_vert):
                x, y = get_topleft_tile_point(i, j)
                hex_img = self.cut_hex(frame_pixels, x, y)
                self.save_hex(hex_img, framenum, hexnum)
                hexnum += 1

    def cut_hex(self, frame_pixels, topleft_x, topleft_y):
        hex_img = Image.new('RGBA', (conf.tile_width, conf.tile_height))
        hex_pixels = hex_img.load()
        for x in range(conf.tile_width):
            for y in range(conf.tile_height):
                if is_in_hex(x, y):
                    if topleft_x == topleft_y and x == 20 and y == 20:
                        print topleft_x, topleft_y, x, y
                    frame_x = (x + topleft_x) % conf.frame_width
                    frame_y = (y + topleft_y) % conf.frame_height
                    color = frame_pixels[frame_x, frame_y]
                else:
                    color = (0, 0, 0, 0)
                hex_pixels[x, y] = color
        return hex_img

    def save_hex(self, hex_img, framenum, hexnum):
        filename = "{}.png".format(self.get_hex_name(framenum, hexnum))
        filepath = os.path.join(self.imgdir, filename)
        hex_img.save(filepath)

    def get_hex_name(self, framenum, hexnum):
        return "{name}_{hexnum:0>2}_{framenum:0>2}".format(
            framenum=framenum, name=self.group_name, hexnum=hexnum
        )

    def handle_sigint(self, signal, frame):
        self.error = "SIGINT"

    def wait_for_finish(self):
        pixel_sum = 0
        while not self.error and pixel_sum < self.pixel_count:
            time.sleep(self.progress_bar_sleep)
            pixel_sum = sum([x.pixels_calculated for x in self.frame_generators])
            print_progress_bar(pixel_sum, self.pixel_count)
