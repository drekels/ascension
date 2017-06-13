from tools.util import FeatureGenerator


class MountainGenerator(FeatureGenerator):
    feature_set_name = "mountain"
    filename = "mountain_meta.yaml"
    feature_types = [
        {"name": "mountain1", "count": 15, "size": 12},
        {"name": "mountain2", "count": 15, "size": 12},
        {"name": "mountain3", "count": 15, "size": 12},
        {"name": "mountain4", "count": 15, "size": 12},
    ]
    terrain_feature_pairing = [
        {
            "terrain": "mountain",
            "pairings": {
                "mountain1": "terrain.features.mountain_1",
                "mountain2": "terrain.features.mountain_1",
                "mountain3": "terrain.features.mountain_1",
                "mountain4": "terrain.features.mountain_1",
            },
        }
    ]
