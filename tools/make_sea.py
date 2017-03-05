import random
import shutil
import os
from threading import Thread
from decimal import Decimal, getcontext

from PIL import Image


def smoothstep(a0, a1, w):
    value = w**3 * (w * (w*6 - 15) + 10)
    return a0 + value *(a1 - a0)


def get_dot_product(v1, v2):
    return sum([a*b for (a, b) in zip(v1, v2)])


def get_coor_set(dimensions):
    if not dimensions:
        yield []
    else:
        dimensions = list(dimensions)
        dimension = dimensions.pop()
        coor_starts = list(get_coor_set(dimensions))
        for i in range(dimension):
            for coor_start in coor_starts:
                coor = list(coor_start)
                coor.append(i)
                yield coor


def get_random_vector(num_dimensions):
    """ Based on http://mathworld.wolfram.com/HyperspherePointPicking.html """
    xn = []
    for _ in range(num_dimensions):
        xn.append(Decimal(random.random())*2 - 1)
    scalar = 1 / (sum([xi**2 for xi in xn])**Decimal('0.5'))
    return normalize([Decimal(xi * scalar) for xi in xn])


def normalize(vector):
    length = sum([x**2 for x in vector])**Decimal('0.5')
    return [x / length for x in vector]


def get_bitlist(number, min_digits=0):
    bitlist = []
    while number:
        bitlist.append(number % 2)
        number = number >> 1
    while len(bitlist) < min_digits:
        bitlist.append(0)
    bitlist.reverse()
    return bitlist


color_map = [
    (-1.0, (32, 134, 135)),
    (-0.3, (41, 139, 140)),
    (0.15, (65, 151, 152)),
    (0.4, (91, 160, 160)),
]



class SeaGenerator(object):
    image_width = 100
    image_height = 100
    perlin_width = 5
    perlin_height = 60
    dimensions = [5, 60, 2]
    perlin_seed = 23
    pixel_size = 1
    decimal_precision = 5
    animation_frame_count = 20
    group_name = "sea"

    @classmethod
    def make_sea(cls, outdir):
        obj = cls()
        obj.start()

    def __init__(self):
        getcontext().prec = self.decimal_precision
        self.perlin = TileablePerlinGenerator(dimensions=self.dimensions, seed=self.perlin_seed)
        self.scaled_width = self.image_width / self.pixel_size
        self.scaled_height = self.image_width / self.pixel_size

    def start(self):
        self.create_dir()
        self.make_images()

    def create_dir(self):
        if os.path.isdir(self.group_name):
            shutil.rmtree(self.group_name)
        os.mkdir(self.group_name)

    def make_images(self):
        for frame in range(self.animation_frame_count):
            thread = Thread(target=self.make_image, args=(frame,))
            thread.start()

    def make_image(self, frame):
        image = Image.new('RGB', (self.image_width, self.image_height))
        pixels = image.load()
        z = Decimal(frame) / self.animation_frame_count
        for i in range(self.scaled_width):
            x = Decimal(i) / self.scaled_width
            for j in range(self.scaled_height):
                y = Decimal(j) / self.scaled_height
                value = self.perlin.get_value(x, y, z)
                for threshhold, c in color_map:
                    if value > threshhold:
                        color = c
                    else:
                        break
                px = i * self.pixel_size
                py = j * self.pixel_size
                for mx in range(self.pixel_size):
                    for my in range(self.pixel_size):
                        pixels[px+mx, py+my] = color
        image.save("{name}/{name}-{num}.png".format(num=frame, name=self.group_name,))

    def get_pixel(self, px, py):
        px = px - px % self.pixel_size
        py = py - py % self.pixel_size
        Decimal(px) * self.perlin_width / self.image_width


class TileablePerlinGenerator(object):
    seed = 0
    dimensions = [1, 2, 3]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        random.seed(self.seed)
        self.generate_vectors()

    def generate_vectors(self):
        self.vectors = {}
        for coor in get_coor_set(self.dimensions):
            self.vectors[tuple(coor)] = get_random_vector(len(self.dimensions))

    def get_value(self, *position):
        normalized = [p * d for (p, d) in zip(position, self.dimensions)]
        anchor_coor = [int(n) % d for (n, d) in zip(normalized, self.dimensions)]
        dot_products = []
        for i in range(2**len(self.dimensions)):
            bitlist = get_bitlist(i, min_digits=len(self.dimensions))
            overflow_coor = [(a + b) for (a, b) in zip(anchor_coor, bitlist)]
            coor = [c % d for (c, d) in zip(overflow_coor, self.dimensions)]
            diff = [n - c for (n, c) in zip(normalized, overflow_coor)]
            vector = self.vectors[tuple(coor)]
            dot_product = get_dot_product(diff, vector)
            dot_products.append(dot_product)

        for i in range(len(self.dimensions)):
            dim_position = normalized[-(i+1)] % 1
            interpolated = []
            for i in range(len(dot_products) / 2):
                left = dot_products[i*2]
                right = dot_products[i*2 + 1]
                interpolated.append(smoothstep(left, right, dim_position))
            dot_products = interpolated

        value = dot_products[0]
        return value
