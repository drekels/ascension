import sys
import random
import os
import shutil
import signal
import time
import math
from threading import Thread
from decimal import Decimal, getcontext


from sortedcontainers import SortedList
import yaml
from PIL import Image


from ascension.perlin import TileablePerlinGenerator
from ascension.settings import AscensionConf as conf


N_HEX_LINE = (0, 1, 0)
S_HEX_LINE = (0, 1, -conf.tile_height)
NW_HEX_LINE = (conf.tile_point_slope, 1, 2 - conf.horz_point_width)
SW_HEX_LINE = (-conf.tile_point_slope, 1, 2 - conf.horz_point_width)
SE_HEX_LINE = (
    conf.tile_point_slope, 1,
    1 - conf.tile_height / 2 - conf.tile_point_slope*(conf.tile_width - 1)
)
NE_HEX_LINE = (
    conf.tile_point_slope, 1,
    1 - conf.tile_height / 2 + conf.tile_point_slope*(conf.tile_width - 1)
)


def use_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def clear_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)
    else:
        shutil.rmtree(path)
        os.makedirs(path)


def line_gtoe(line, x, y):
    a, b, c = line
    if b == 0:
        raise ZeroDivisionError(
            "Cannot determine if point is above or below vertical line"
        )
    return y >= (-a/b)*x - (c/b)


def line_gt(line, x, y):
    a, b, c = line
    if b == 0:
        raise ZeroDivisionError(
            "Cannot determine if point is above or below vertical line"
        )
    return y > (-a/b)*x - (c/b)


def line_ltoe(line, x, y):
    a, b, c = line
    if b == 0:
        raise ZeroDivisionError(
            "Cannot determine if point is above or below vertical line"
        )
    return y <= (-a/b)*x - (c/b)


def line_lt(line, x, y):
    a, b, c = line
    if b == 0:
        raise ZeroDivisionError(
            "Cannot determine if point is above or below vertical line"
        )
    return y < (-a/b)*x - (c/b)


def get_distance_to_line(x, y, line):
    # Thanks wikipedia
    a, b, c = line
    print x, y, a, b, c, abs(a*x + b*y + c)
    return abs(a*x + b*y + c) / Decimal(math.sqrt(a**2 + b**2))


def get_line_through_point(x, y, slope_num, slope_den):
    if slope_den == 0:
        return 1, 0, -x
    slope = Decimal(slope_num) / Decimal(slope_den)
    return -slope, 1, slope*x - y


def line_eq(line1, line2):
    a1, b1, c1 = line1
    a2, b2, c2 = line2
    if b1 == 0 and b2 == 0:
        return isclose(Decimal(a1) / Decimal(c1), Decimal(a2) / Decimal(c2))
    return (
            isclose(Decimal(a1) / Decimal(b1), Decimal(a2), Decimal(b2))
        and isclose(Decimal(c1) / Decimal(b1), Decimal(c2), Decimal(b2))
    )


def isclose(a, b, rel_tol=Decimal("1e-09"), abs_tol=Decimal("0.0")):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def get_line_intersection(line1, line2):
    a1, b1, c1 = line1
    a2, b2, c2 = line2
    if b1 == 0 and b2 == 0:
        raise ZeroDivisionError("Cannot compute intersection of parallel lines")
    elif b1 == 0:
        x = -c1 / a1
        y = (-a2 / b2) * x - (c2 / b2)
        return x, y
    elif b2 == 0:
        x = -c2 / a2
        slope1 = (-a1 / b1)
        yint1 = (-c1 / b1)
    elif a1 / b1 == a2 / b2:
        raise ZeroDivisionError("Cannot compute intersection of parallel lines")
    else:
        slope1 = (-a1 / b1)
        slope2 = (-a2 / b2)
        yint1 = (-c1 / b1)
        yint2 = (-c2 / b2)
        x = (yint2 - yint1) / (slope1 - slope2)
    y = slope1 * x + yint1
    return x, y


def get_slope(line):
    a, b, c = line
    if b == 0:
        return "undefined"
    return - Decimal(a) / Decimal(b)


def get_line_through(x1, y1, x2, y2):
    if x1 == x2 and y1 == y2:
        raise ZeroDivisionError("Cannot create line between the same point")
    slope_num = y2 - y1
    slope_den = x2 - x1
    return get_line_through_point(x1, y1, slope_num, slope_den)


def get_distance_between_points(x1, y1, x2, y2):
    return Decimal(math.sqrt((x2 - x1)**2 + (y2 - y1)**2))


def get_distance_to_line_segment(x, y, x1, y1, x2, y2):
    a1, b1, c1 = get_line_through(x1, y1, x2, y2)
    distance1 = get_distance_between_points(x, y, x1, y1)
    distance2 = get_distance_between_points(x, y, x2, y2)
    close_x, close_y, other_x, other_y, close_dist = (
        distance1 <= distance2
        and (x1, y1, x2, y2, distance1)
        or (x2, y2, x1, y1, distance2)
    )
    if a1 == 0:
        print x, close_x, other_x, (x < close_x) == (other_x < close_x)
        if (x < close_x) == (other_x < close_x):
            return abs(y - y1)
        else:
            return close_dist
    cut_off = get_line_through_point(close_x, close_y, b1, a1)
    print (a1, b1, c1), cut_off
    if line_lt(cut_off, x, y) == line_lt(cut_off, other_x, other_y):
        print x, y, (a1, b1, c1)
        return get_distance_to_line(x, y, (a1, b1, c1))
    else:
        return close_dist


def is_in_hex(x, y):
    value = (
            line_gtoe(N_HEX_LINE, x, y)
        and line_lt(S_HEX_LINE, x, y)
        and line_gtoe(NW_HEX_LINE, x, y)
        and line_ltoe(SW_HEX_LINE, x, y)
        and line_ltoe(SE_HEX_LINE, x, y)
        and line_gtoe(NE_HEX_LINE, x, y)
    )
    return value


def get_topleft_tile_point(i, j):
    x = i * (conf.tile_center_width + conf.horz_point_width - 1)
    y = j * conf.tile_height - (i % 2) * conf.tile_height / 2
    return x, y


def shade_color(color, shader):
    shader_alpha = shader[3]
    r = lerp(color[0], shader[0], shader_alpha)
    g = lerp(color[1], shader[1], shader_alpha)
    b = lerp(color[2], shader[2], shader_alpha)
    return (int(r), int(g), int(b), 255)


def lerp(a, b, r):
    return a + r * (b-a)


def print_progress_bar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 70, fill = u'\u2588'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print u'\r{} |{}| {}% {}'.format(prefix, bar, percent, suffix),
    if iteration == total:
        print
    sys.stdout.flush()


def get_all_hex_edges_touched(x, y, exclusion_size):
    edges = [
        ('NW', NW_HEX_LINE), ('SW', SW_HEX_LINE), ('N', N_HEX_LINE),
        ('S', S_HEX_LINE), ('NE', NE_HEX_LINE), ('SE', SE_HEX_LINE),
    ]
    for label, edge in edges:
        if is_on_hex_edge(edge, x, y, exclusion_size):
            yield label


def is_on_hex_edge(edge, x, y, exclusion_size):
    dis = get_distance_to_line(x, y, edge)
    return dis < exclusion_size


class FeatureGenerator(object):
    max_attempts = 10
    random_seed = 10

    @classmethod
    def make_features(cls, **kwargs):
        obj = cls(**kwargs)
        obj.start()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.excluded_points = {}
        self.done = False
        self.final_frame = None
        self.feature_tiles = []
        self.success_count = 0
        self.attempts = 0
        self.feature_types = sorted(self.feature_types, key=lambda x: x["size"])
        random.seed(self.random_seed)

    def start(self):
        self.create_exclusion_maps()
        while self.attempts < self.max_attempts:
            self.attempts += 1
            self.attempt_feature_map()
        print "{} / {} Successes".format(self.success_count, self.attempts)
        if not self.final_frame:
            print "FAILED"
        else:
            self.cut_feature_tiles()
            self.save_to_outfile()
            print "SUCCESS"

    def cut_feature_tiles(self):
        for i in range(conf.frame_tile_count_horz):
            for j in range(conf.frame_tile_count_vert):
                num = i + 2*j
                x, y = get_topleft_tile_point(i, j)
                feature_tile = self.cut_feature_tile(x, y)
                self.feature_tiles.append({
                    "name": "{}_{}".format(self.feature_set_name, num),
                    "features": feature_tile,
                    "terrain_feature_pairing": self.terrain_feature_pairing,
                })

    def cut_feature_tile(self, topleft_x, topleft_y):
        features = []
        for feature in self.final_frame:
            x, y = feature['x'], feature['y']
            tile_x = (x - topleft_x) % conf.frame_width
            tile_y = (y - topleft_y) % conf.frame_height
            if is_in_hex(tile_x, tile_y):
                edges = list(get_all_hex_edges_touched(tile_x, tile_y, 4))
                adjusted_feature = {
                    'x': tile_x - conf.tile_width / 2,
                    'y': conf.tile_height / 2 - tile_y,
                    'name': feature['name'],
                    'edges': edges,
                }
                features.append(adjusted_feature)
        return features

    def attempt_feature_map(self):
        feature_map = []
        points_remaining = {}
        features_to_place = []
        for feature in self.feature_types:
            for i in range(feature["count"]):
                features_to_place.append(feature)
        for i in range(conf.frame_width):
            for j in range(conf.frame_height):
                points_remaining[(i, j)] = None
        while points_remaining and features_to_place:
            feature_data = features_to_place.pop()
            exclusion_size = feature_data['size']
            point_i = random.randint(0, len(points_remaining)-1)
            point = points_remaining.keys()[point_i]
            points_remaining.pop(point)
            feature = {
                'name': feature_data['name'],
                'x': point[0],
                'y': point[1],
                'size': exclusion_size
            }
            feature["x"], feature["y"] = point
            feature["size"] = exclusion_size
            feature_map.append(feature)
            self.apply_exclusion(points_remaining, exclusion_size, *point)
        if not features_to_place:
            feature_map.sort(key=lambda x: (x['x'], x['y']))
            self.success_count += 1
            if not self.final_frame:
                self.final_frame = feature_map
        print "Final point_count = {}".format(len(points_remaining))

    def apply_exclusion(self, points_remaining, size, x, y):
        e_map = self.exclusion_maps[size]
        for i, j in e_map:
            exclude = (x+i) % conf.frame_width, (y+j) % conf.frame_height
            points_remaining.pop(exclude, None)

    def create_exclusion_maps(self):
        self.exclusion_maps = {}
        for feature in self.feature_types:
            size = feature["size"]
            if size not in self.exclusion_maps:
                self.exclusion_maps[size] = self.create_exclusion_map(size)

    def create_exclusion_map(self, size):
        e_map = []
        self.try_add_to_exclusion_map(e_map, size, 0, 0)
        return e_map

    def try_add_to_exclusion_map(self, e_map, size, x, y):
        y_dist = y / conf.perspective_sin
        if (x, y) in e_map or x**2 + y_dist**2 > size**2:
            return
        e_map.append((x, y))
        self.try_add_to_exclusion_map(e_map, size, x+1, y)
        self.try_add_to_exclusion_map(e_map, size, x, y+1)
        self.try_add_to_exclusion_map(e_map, size, x-1, y)
        self.try_add_to_exclusion_map(e_map, size, x, y-1)

    def save_to_outfile(self):
        d = {
            "feature_maps": self.feature_tiles
        }
        use_dir(self.outdir)
        filepath = os.path.join(self.outdir, self.filename)
        with open(filepath, 'w') as f:
            f.write(yaml.dump(d))


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


class BaseGenerator(object):

    @classmethod
    def generate(cls, **kwargs):
        obj = cls(**kwargs)
        obj.start()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TerrainGenerator(BaseGenerator):
    decimal_precision = 5
    animation_frame_count = 1
    animation_duration = 0
    animation_meta_filename = "meta.yaml"
    progress_bar_sleep = 5
    border = []

    def __init__(self, **kwargs):
        super(TerrainGenerator, self).__init__(**kwargs)
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
            self.make_border_map()
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

    def make_border_map(self):
        self.border_map = {}
        max_border = 0
        while len(self.border_map) < conf.tile_width * conf.tile_height:
            for x in range(conf.tile_width):
                for y in range(conf.tile_height):
                    self.get_border_level(x, y, max_border=max_border)
            max_border += 1

    def get_border_level(self, x, y, max_border=None):
        if (x, y) not in self.border_map:
            if is_in_hex(x, y):
                right = self.border_map.get((x+1, y), 1000)
                left = self.border_map.get((x-1, y), 1000)
                up = self.border_map.get((x, y-1), 1000)
                down = self.border_map.get((x, y+1), 1000)
                if x+1 >= conf.tile_width:
                    right = -1
                if x-1 < 0:
                    left = -1
                if y-1 < 0:
                    up = 0
                if y+1 >= conf.tile_height:
                    down = -1
                value = min([right, left, up, down]) + 1
            else:
                value = -1
            if value < max_border:
                self.border_map[(x, y)] = value
        return self.border_map.get((x, y))

    def create_dir(self):
        self.imgdir = os.path.join(self.outdir, self.group_name)
        use_dir(self.imgdir)

    def make_images(self):
        self.threads = []
        for framenum in range(self.animation_frame_count):
            thread = Thread(target=self.try_make_frame, args=(framenum,))
            self.threads.append(thread)
            thread.start()

    def threads_running(self):
        return sum([thread.isAlive() for thread in self.threads])

    def make_animations(self):
        if not self.animation_duration:
            return
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
            z=z, perlin_generators=self.perlin_generators, color_map=self.color_map,
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
                    frame_x = (x + topleft_x) % conf.frame_width
                    frame_y = (y + topleft_y) % conf.frame_height
                    color = frame_pixels[frame_x, frame_y]
                    border_level = self.get_border_level(x, y)
                    if border_level < len(self.border):
                        border_color = self.border[border_level]
                        if len(border_color) == 2:
                            border_color = border_color[y*2 / conf.tile_height > 0 and 1 or 0]
                        color = shade_color(color, border_color)
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
