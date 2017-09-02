from tools.make_atlas import AtlasGenerator
from tools.make_sea import SeaGenerator
from tools.make_forest import ForestGenerator
from tools.make_grassland import GrasslandGenerator
from tools.make_mountain import MountainGenerator
import sys


if sys.argv[1] == "make_atlas":
    AtlasGenerator.make_atlas(*sys.argv[2:])
elif sys.argv[1] == "make_sea":
    SeaGenerator.make_sea(outdir=sys.argv[2])
elif sys.argv[1] == "make_grassland":
    GrasslandGenerator.make_sea(outdir=sys.argv[2])
elif sys.argv[1] == "make_forest":
    ForestGenerator.make_features(outdir=sys.argv[2])
elif sys.argv[1] == "make_mountain":
    MountainGenerator.make_features(outdir=sys.argv[2])
else:
    raise Exception("No manage command '{}'".format(sys.argv[1]))
