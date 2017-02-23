import sys
import os
import json
import yaml
import shutil
from sprite.atlas import Atlas
from sprite.component import SpriteComponent
from ascension.ascsprite import AscAnimation
from PIL import Image

class AscensionAtlas(Atlas):

    def __init__(self, *args, **kwargs):
        self.animations = {}
        super(AscensionAtlas, self).__init__(*args, **kwargs)

    def add_animation(self, animation):
        if animation.name in self.animations:
            raise KeyError(
                "Animation named '{}' added a second time to atlas".format(animation.name)
            )
        self.animations[animation.name] = animation

    def get_meta(self):
        for animation in self.animations.values():
            order = 0
            tokens = animation.name.split(".")[:-1]
            for stage in animation.stages:
                stage.order = order
                stage.component_name = ".".join(tokens + [stage.component_name])
                stage.component = self.components[stage.component_name]
                order += 1
        components_meta = super(AscensionAtlas, self).get_meta()
        animation_meta = []
        for animation in self.animations.values():
            animation_meta.append(animation.__getstate__())
        return {
            "components": components_meta,
            "animations": animation_meta
        }


def remove_extension(filepath):
    return ".".join(filepath.split(".")[:-1])


class AtlasGenerator(object):
    load_map = {
        ("unit",): "load_unit_image",
        ("terrain", "features"): "load_feature_image",
    }
    data_dir = "data"
    img_dir = os.path.join(data_dir, "img")
    x2_dir = os.path.join(img_dir, "x2")

    @classmethod
    def make_atlas(cls, base_directory):
        inst = cls(base_directory)
        inst.load_images()
        inst.generate_atlas()
        if os.path.isdir(cls.img_dir):
            shutil.rmtree(cls.img_dir)
        os.mkdir(cls.img_dir)
        os.mkdir(cls.x2_dir)
        inst.save_all_images()
        inst.save_atlas()

    def __init__(self, base_directory):
        self.base_directory = base_directory

    def load_images(self):
        self.components = {}
        self.extra_component_meta = {}
        self.animations = []
        self.load_image_dir(self.base_directory)
        self.update_extra_component_meta()

    def update_extra_component_meta(self):
        for component_name, extra_meta in self.extra_component_meta.items():
            component = self.components[component_name]
            if getattr(component, "anchor_x_slide_1", False):
                for key in extra_meta:
                    if key.endswith("_x"):
                        extra_meta[key] += 1
            if getattr(component, "anchor_y_slide_1", False):
                for key in extra_meta:
                    if key.endswith("_y"):
                        extra_meta[key] += 1
            component.extra_meta.update(extra_meta)

    def generate_atlas(self):
        self.atlas = AscensionAtlas(
            "ASCENSION ATLAS\n{size}\nCopywrite Kevin Steffler (c)",
            min_size = (256, 256)
        )
        for component in self.components.values():
            self.atlas.add_component(component)
        for animation in self.animations:
            self.atlas.add_animation(animation)

    def save_all_images(self):
        for component_name, component in self.atlas.components.items():
            filename = "{}.png".format(component_name)
            filepath = os.path.join(self.img_dir, filename)
            x2_filepath = os.path.join(self.x2_dir, filename)
            component.image.save(filepath, format="PNG")
            width, height = component.image.width, component.image.height
            x2_image = component.image.resize((width*2, height*2))
            x2_image.save(x2_filepath, format="PNG")


    def save_atlas(self):
        meta_file_name = os.path.join(self.img_dir, "ASCENSION_ATLAS_META.json")
        img_file_name = os.path.join(self.img_dir, "ASCENSION_ATLAS.png")
        with open(meta_file_name, "w") as f:
            json.dump(self.atlas.get_meta(), f, indent=4)
        self.atlas.dump_atlas(img_file_name)

    def load_image_dir(self, directory, tokens=[]):
        for tail in os.listdir(directory):
            if "DS_Store" in tail:
                continue
            path = os.path.join(directory, tail)
            if os.path.isfile(path):
                if path.endswith(".yaml"):
                    self.load_extra_meta(path, tokens)
                else:
                    self.load_image(path, tokens)
            else:
                self.load_image_dir(path, tokens + [tail])

    def load_image(self, image_path, tokens):
            tokens_temp = list(tokens)
            load_image_func = None
            while tokens_temp and not load_image_func:
                load_image_func_name = self.load_map.get(tuple(tokens_temp), None)
                if load_image_func_name:
                    load_image_func = getattr(self, load_image_func_name)
                tokens_temp.pop()
            (load_image_func or self.load_image_default)(image_path, tokens)

    def load_extra_meta(self, meta_path, tokens):
        with open(meta_path) as f:
            data = yaml.load(f)
        extra_component_meta = data.get("components", [])
        for ecm in extra_component_meta:
            component_name = ".".join(tokens + [ecm.pop("name")])
            self.add_extra_component_meta(component_name, ecm)
        animations = data.get("animations", [])
        for animation_data in animations:
            animation_data["name"] = ".".join(tokens + [animation_data["name"]])
            animation = AscAnimation.load(animation_data)
            self.animations.append(animation)

    def load_image_default(self, image_path, tokens):
        filename = os.path.basename(image_path)
        name = ".".join(tokens + [remove_extension(filename)])
        component = SpriteComponent(name, image_path)
        self.add_center_anchor(component)
        self.components[name] = component

    def load_feature_image(self, image_path, tokens):
        filename = os.path.basename(image_path)
        name = ".".join(tokens + [remove_extension(filename)])
        base_component = SpriteComponent(name, image_path)
        self.add_center_anchor(base_component)
        component = shade_edges(base_component)
        self.components[name] = component

    def load_unit_image(self, image_path, tokens):
        filename = os.path.basename(image_path)
        name = ".".join(tokens + [remove_extension(filename)])
        base_component = SpriteComponent(name, image_path)
        self.add_center_anchor(base_component)
        component = shade_edges(base_component)
        self.components[name] = component

    def add_center_anchor(self, component):
        self.add_extra_component_meta(component.name, {
            "center_x": component.width / 2,
            "center_y": component.height / 2,
        })

    def add_extra_component_meta(self, component_name, ecm):
        if component_name not in self.extra_component_meta:
            self.extra_component_meta[component_name] = {}
        for key, value in ecm.items():
            if key in self.extra_component_meta[component_name]:
                raise KeyError(
                    "Already have extra component meta attr '{}' for component '{}'".format(
                    key, component_name)
                )
            self.extra_component_meta[component_name][key] = value


def adjacent(img, x, y):
    for i, j in (x+1, y), (x-1, y), (x, y+1), (x, y-1):
        if 0 <= i < img.size[0] and 0 <= j < img.size[1]:
            yield img.getpixel((i, j))


def shade_edges(base_component, shade_a=50):
    newimg = Image.new("RGBA", [a+2 for a in base_component.image.size], (0, 0, 0, 0))
    arr = newimg.load()
    newimg.paste(base_component.image, (1, 1))
    width, height = newimg.size
    anchor_x_slide_1 = False
    anchor_y_slide_1 = False
    for x in range(width):
        for y in range(height):
            r, g, b, a = newimg.getpixel((x, y))
            if not a and [adj for adj in adjacent(newimg, x, y) if adj[3] == 255]:
                arr[x, y] = (0, 0, 0, shade_a)
    if not [x for x in range(newimg.size[0]) if newimg.getpixel((x, 0)) != (0, 0, 0, 0)]:
        # Added nothing to top, delete top row
        newimg = newimg.crop((0, 1, newimg.size[0], newimg.size[1]))
    else:
        # Added top row, slide x values
        anchor_y_slide_1 = True
    if not [x for x in range(newimg.size[0]) if newimg.getpixel((x, newimg.size[1]-1)) != (0, 0, 0, 0)]:
        # Added nothing to bottom, delete bottom row
        newimg = newimg.crop((0, 0, newimg.size[0], newimg.size[1]-1))
    if not [y for y in range(newimg.size[1]) if newimg.getpixel((0, y)) != (0, 0, 0, 0)]:
        # Added nothing to left, delete left column
        newimg = newimg.crop((1, 0, newimg.size[0], newimg.size[1]))
    else:
        # Added left column, slide x values
        anchor_x_slide_1 = True
    if not [y for y in range(newimg.size[1]) if newimg.getpixel((newimg.size[0]-1, y)) != (0, 0, 0, 0)]:
        # Added nothing to right, delete right column
        newimg = newimg.crop((0, 0, newimg.size[0]-1, newimg.size[1]))
    component = SpriteComponent(name=base_component.name, image=newimg)
    component.anchor_x_slide_1 = anchor_x_slide_1
    component.anchor_y_slide_1 = anchor_y_slide_1
    return component


if __name__ == '__main__':
    AtlasGenerator.make_atlas(sys.argv[1])
