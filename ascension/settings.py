from ascension.util import SettingSet, Singleton, SettingBased
from pykfs.kfslog import CONSOLE_HANDLER, CONSOLE_FORMATTER
import yaml
import os



CONF_FILE_NAME = "ascension_conf.yaml"


game_settings = SettingSet([
    {
        "name": "target_frame_rate",
        "default": 60,
    },
    {
        "name": "slow_frame_log_level",
        "default": "WARNING"
    },
    {
        "name": "window_size",
        "default": (640, 480),
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
        "name": "atlas_image",
        "default": "data/ASCENSION_ATLAS.png",
    },
    {
        "name": "atlas_meta",
        "default": "data/ASCENSION_ATLAS_META.json"
    },
    {
        "name": "window_width",
        "default": 1000
    },
    {
        "name": "window_height",
        "default": 600,
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
    }


])


class AscensionConf(SettingBased):
    __metaclass__ = Singleton
    settingset = game_settings

    def __init__(self):
        values = {}
        if os.path.isfile(CONF_FILE_NAME):
            with open(CONF_FILE_NAME) as f:
                values = yaml.load(f) or {}
        super(AscensionConf, self).__init__(**values)

class PlayerConf(SettingBased):
    __metaclass__ = Singleton
    settingset = player_settings
