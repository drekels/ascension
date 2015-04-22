import sys
import os
import json
from sprite.atlas import Atlas
from sprite.component import SpriteComponent


def remove_extension(filepath):
    return ".".join(filepath.split("."))


def make_atlas(image_directory):
    a = Atlas(
        "ASCENSION ATLAS\n{size}\nCopywrite Kevin Steffler (c)",
        min_size = (256, 256)
    )
    for filename in os.listdir(image_directory):
        filepath = os.path.join(image_directory, filename)
        name = remove_extension(filename)
        component = SpriteComponent(name, filepath)
        a.add_component(component)
    a.dump_atlas("data/ASCENSION_ATLAS.png")
    with open("data/ASCENSION_ATLAS_META.json", "w") as f:
        json.dump(a.get_meta(), f, indent=4)


if __name__ == '__main__':
    make_atlas(sys.argv[1])
