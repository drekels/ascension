import sys
import random
import os


import yaml


from ascension.settings import AscensionConf as conf


N_HEX_LINE = (0, 0)
S_HEX_LINE = (0, conf.tile_height)
NW_HEX_LINE = -conf.tile_point_slope, conf.horz_point_width - 1
SW_HEX_LINE = conf.tile_point_slope, conf.horz_point_width - 1
SE_HEX_LINE = (
    -conf.tile_point_slope,
    conf.tile_height / 2 - 1 + conf.tile_point_slope*(conf.tile_width - 1)
)
NE_HEX_LINE = (
    conf.tile_point_slope,
    conf.tile_height / 2 - 1 - conf.tile_point_slope*(conf.tile_width - 1)
)


def line_gtoe(line, x, y):
    a, b = line
    return y >= a*x + b


def line_gt(line, x, y):
    a, b = line
    return y > a*x + b


def line_ltoe(line, x, y):
    a, b = line
    return y <= a*x + b


def line_lt(line, x, y):
    a, b = line
    return y < a*x + b


def get_distance_to_line(x, y, line):
    # Thanks wikipedia
    line_a, line_b = line
    a = -line_a
    b = 1
    c = -line_b
    return abs(a*x + b*y + c) / (a**2 + b**2)


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
        filepath = os.path.join(self.outdir, self.filename)
        with open(filepath, 'w') as f:
            f.write(yaml.dump(d))
