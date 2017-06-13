from tools.util import FeatureGenerator


class ForestGenerator(FeatureGenerator):
    feature_set_name = "forest"
    filename = "forest_meta.yaml"
    feature_types = [
        {"name": "tree1", "count": 40, "size": 7},
        {"name": "tree2", "count": 40, "size": 7},
        {"name": "tree3", "count": 40, "size": 7},
        {"name": "tree4", "count": 40, "size": 7},
    ]
    terrain_feature_pairing = [
        {
            "terrain": "forest",
            "pairings": {
                "tree1": "terrain.features.c_tree_1",
                "tree2": "terrain.features.d_tree_1",
                "tree3": "terrain.features.dead_tree_1",
                "tree4": "terrain.features.c_tree_1",
            },
        }
    ]
