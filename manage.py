from tools.make_atlas import AtlasGenerator
import sys


if sys.argv[1] == "make_atlas":
    AtlasGenerator.make_atlas(sys.argv[2])
else:
    raise Exception("No manage command '{}'".format(sys.argv[1]))
