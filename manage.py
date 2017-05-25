from tools.make_atlas import AtlasGenerator
from tools.make_sea import SeaGenerator
from tools.make_forest import ForestGenerator
import sys


if sys.argv[1] == "make_atlas":
    AtlasGenerator.make_atlas(base_directory=sys.argv[2])
elif sys.argv[1] == "make_sea":
    SeaGenerator.make_sea(outdir=sys.argv[2])
elif sys.argv[1] == "make_forest":
    ForestGenerator.make_forest(outdir=sys.argv[2])
else:
    raise Exception("No manage command '{}'".format(sys.argv[1]))
