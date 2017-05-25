import random
import os
import yaml


from ascension.settings import AscensionConf as conf
from tools.util import is_in_hex, get_topleft_tile_point


feature_setup = [
    {"name": "tree1", "count": 20, "size": 10},
    {"name": "tree2", "count": 20, "size": 10},
    {"name": "tree3", "count": 20, "size": 10},
    {"name": "tree4", "count": 20, "size": 10},
]



class ForestGenerator(object):
    max_attempts = 10
    random_seed = 10
    filename = "forest_meta.yaml"

    @classmethod
    def make_forest(cls, **kwargs):
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
        self.feature_setup = sorted(feature_setup, key=lambda x: x["size"])
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
                    "name": "forest{}".format(num),
                    "features": feature_tile,
                })

    def cut_feature_tile(self, topleft_x, topleft_y):
        features = []
        for feature in self.final_frame:
            x, y = feature['x'], feature['y']
            tile_x = (x - topleft_x) % conf.frame_width
            tile_y = (y - topleft_y) % conf.frame_height
            if is_in_hex(tile_x, tile_y):
                features.append(feature)
        return features

    def attempt_feature_map(self):
        feature_map = []
        points_remaining = {}
        features_to_place = []
        for feature in self.feature_setup:
            for i in range(feature["count"]):
                features_to_place.append(feature)
        for i in range(conf.frame_width):
            for j in range(conf.frame_height):
                points_remaining[(i, j)] = None
        while points_remaining and features_to_place:
            feature_setup = features_to_place.pop()
            point_i = random.randint(0, len(points_remaining)-1)
            point = points_remaining.keys()[point_i]
            points_remaining.pop(point)
            feature = dict([('name', feature_setup['name'])])
            feature["x"], feature["y"] = point
            feature_map.append(feature)
            self.apply_exclusion(points_remaining, feature_setup["size"], *point)
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
        for feature in feature_setup:
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
