import sys
import os
import json
from sprite.atlas import Atlas
from sprite.component import SpriteComponent
from PIL import Image


def remove_extension(filepath):
    return ".".join(filepath.split(".")[:-1])


class AtlasGenerator(object):
    load_map = {
        ("unit",): "load_unit_image"
    }

    @classmethod
    def make_atlas(cls, base_directory):
        inst = cls(base_directory)
        inst.generate_atlas()
        inst.save_atlas()

    def __init__(self, base_directory):
        self.base_directory = base_directory

    def generate_atlas(self):
        self.atlas = Atlas(
            "ASCENSION ATLAS\n{size}\nCopywrite Kevin Steffler (c)",
            min_size = (256, 256)
        )
        self.load_image_dir(self.base_directory)

    def save_atlas(self):
        with open("data/ASCENSION_ATLAS_META.json", "w") as f:
            json.dump(self.atlas.get_meta(), f, indent=4)
        self.atlas.dump_atlas("data/ASCENSION_ATLAS.png")

    def load_image_dir(self, directory, tokens=[]):
        for tail in os.listdir(directory):
            if "DS_Store" in tail:
                continue
            path = os.path.join(directory, tail)
            if os.path.isfile(path):
                tokens_temp = list(tokens)
                load_image_func = None
                while tokens_temp and not load_image_func:
                    load_image_func_name = self.load_map.get(tuple(tokens_temp), None)
                    if load_image_func_name:
                        load_image_func = getattr(self, load_image_func_name)
                    tokens_temp.pop()
                (load_image_func or self.load_image)(path, tokens)
            else:
                self.load_image_dir(path, tokens + [tail])

    def load_image(self, image_path, tokens):
        filename = os.path.basename(image_path)
        name = ".".join(tokens + [remove_extension(filename)])
        component = SpriteComponent(name, image_path)
        self.atlas.add_component(component)

    def load_unit_image(self, image_path, tokens):
        filename = os.path.basename(image_path)
        name = ".".join(tokens + [remove_extension(filename)])
        base_component = SpriteComponent(name, image_path)
        img = shade_edges(base_component.image)
        self.atlas.add_component(SpriteComponent(name=base_component.name, image=img))
        img.save("{}_temp.png".format("_".join(tokens)), "PNG")

def adjacent(img, x, y):
    for i, j in (x+1, y), (x-1, y), (x, y+1), (x, y-1):
        if 0 <= i < img.size[0] and 0 <= j < img.size[1]:
            yield img.getpixel((i, j))

def shade_edges(img, shade_a=50):
    newimg = Image.new("RGBA", [a+2 for a in img.size], (0, 0, 0, 0))
    arr = newimg.load()
    newimg.paste(img, (1, 1))
    width, height = newimg.size
    for x in range(width):
        for y in range(height):
            r, g, b, a = newimg.getpixel((x, y))
            if not a and [adj for adj in adjacent(newimg, x, y) if adj[3] == 255]:
                arr[x, y] = (0, 0, 0, shade_a)
    if not [x for x in range(newimg.size[0]) if newimg.getpixel((x, 0)) != (0, 0, 0, 0)]:
        newimg = newimg.crop((0, 1, newimg.size[0], newimg.size[1]))
    if not [x for x in range(newimg.size[0]) if newimg.getpixel((x, newimg.size[1]-1)) != (0, 0, 0, 0)]:
        newimg = newimg.crop((0, 0, newimg.size[0], newimg.size[1]-1))
    if not [y for y in range(newimg.size[1]) if newimg.getpixel((0, y)) != (0, 0, 0, 0)]:
        newimg = newimg.crop((1, 0, newimg.size[0], newimg.size[1]))
    if not [y for y in range(newimg.size[1]) if newimg.getpixel((newimg.size[0]-1, y)) != (0, 0, 0, 0)]:
        newimg = newimg.crop((0, 0, newimg.size[0]-1, newimg.size[1]))
    return newimg


if __name__ == '__main__':
    AtlasGenerator.make_atlas(sys.argv[1])
