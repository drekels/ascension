from tools.make_atlas import AtlasGenerator
from tools.make_sea import SeaGenerator
import sys


if sys.argv[1] == "make_atlas":
    AtlasGenerator.make_atlas(sys.argv[2])
elif sys.argv[1] == "make_sea":
    SeaGenerator.make_sea(sys.argv[2])
else:
    raise Exception("No manage command '{}'".format(sys.argv[1]))
