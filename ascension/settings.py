from ascension.util import SettingSet, Singleton, SettingBased
from pykfs.kfslog import CONSOLE_HANDLER, CONSOLE_FORMATTER
import yaml
import os
import math



CONF_FILE_NAME = "ascension_conf.yaml"


game_settings = SettingSet([
    {
        "name": "target_frame_rate",
        "default": 60,
        "parse": int,
    },
    {
        "name": "slow_frame_log_level",
        "default": "WARNING"
    },
    {
        "name": "logging",
        "default": {
            "version": 1,
            "loggers": {
                "ascension": {
                    "handlers": ["console"],
                    "level": "INFO",
                },
            },
            "handlers": {
                "console": CONSOLE_HANDLER,
            },
            "formatters": {
                "console": CONSOLE_FORMATTER,
            },
        }
    },
    {
        "name": "logging_append",
        "default": {}
    },
    {
        "name": "img_dir",
        "default": "data/img/x3",
    },
    {
        "name": "atlas_image",
        "default": "data/img/ASCENSION_ATLAS.png",
    },
    {
        "name": "atlas_meta",
        "default": "data/img/ASCENSION_ATLAS_META.json"
    },
    {
        "name": "window_width",
        "default": 1500,
        "parse": int,
    },
    {
        "name": "window_height",
        "default": 800,
        "parse": int,
    },
    {
        "name": "disabled_profilers",
        "default": []
    },
    {
        "name": "sprite_scale",
        "default": 3,
        "parse": int,
    },
    {
        "name": "tile_width",
        "default": 71,
        "parse": int,
    },
    {
        "name": "tile_height",
        "default": 30,
        "parse": int,
    },
    {
        "name": "horz_point_width",
        "default": 16,
        "parse": int,
    },
    {
        "name": "frame_tile_count_horz",
        "default": 2,
        "parse": int,
    },
    {
        "name": "frame_tile_count_vert",
        "default": 2,
        "parse": int,
    },
])

player_settings = SettingSet([
    {
        "name": "key_bindings",
        "default": {
        },
    },
    {
        "name": "scroll_speed",
        "default": 400,
        "parse": int,
    },
    {
        "name": "unit_move_speed",
        "default": 50
    }
])

def calc_property(func):
    def new_func(self):
        cache_name = "_{}".format(func.__name__)
        if not hasattr(self, cache_name):
            setattr(self, cache_name, func(self))
        return getattr(self, cache_name)
    return property(new_func)


class AscensionConf(SettingBased):
    __metaclass__ = Singleton
    settingset = game_settings

    def __init__(self):
        values = {}
        if os.path.isfile(CONF_FILE_NAME):
            with open(CONF_FILE_NAME) as f:
                values = yaml.load(f) or {}
        super(AscensionConf, self).__init__(**values)

    @calc_property
    def perspective_sin(self):
        i = self.tile_height / 2.0
        x = self.tile_width / 2.0
        z = self.tile_width / 2.0 - self.horz_point_width
        return i / math.sqrt(x**2-z**2)

    @calc_property
    def diagonal_distance_multiplier(self):
        return math.sqrt(self.perspective_sin**2 + 3) / 2

    @calc_property
    def tile_point_slope(self):
        return self.tile_height / 2 / (self.horz_point_width - 1)

    @calc_property
    def tile_center_width(self):
        return self.tile_width - 2*self.horz_point_width

    @calc_property
    def frame_width(self):
        return (
            self.frame_tile_count_horz * (self.tile_center_width+self.horz_point_width-1)
        )

    @calc_property
    def frame_height(self):
        return self.frame_tile_count_vert * self.tile_height

    @calc_property
    def frame_pixel_count(self):
        return self.frame_width * self.frame_height


AscensionConf.reset()


class PlayerConf(SettingBased):
    __metaclass__ = Singleton
    settingset = player_settings
