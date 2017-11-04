DISTRIBUTION_NAME := ascension
IGNORE_DIRECTORY := ignore

TOOL_DIR := tools
IMAGE_DIR := images
GENERATED_IMAGES_DIR := gen/images
GENERATED_TERRAIN_DIR := $(GENERATED_IMAGES_DIR)/terrain
TERRAIN_IMAGE_DIR := $(IMAGE_DIR)/terrain

PYTHON_FILES = $(shell find . -name \*.py -not -path "./$(TOOL_DIR)/*" -not -path \
               "./$(TOOL_DIR)/*" -not -path "./test/*" -not -name setup.py)

MANAGE_SCRIPT = manage.py



TOOL_SCRIPTS = $(shell find $(TOOL_DIR) -name \*.py)
IMAGE_FILES = $(shell find $(IMAGE_DIR) -name \*.png)
ANIMATION_META = $(shell find $(IMAGE_DIR) -name \*.yaml)

SAMPLE_ENV := $(IGNORE_DIRECTORY)/$(DISTRIBUTION_NAME)SampleEnv
SAMPLE_ENV_PIP := $(SAMPLE_ENV)/bin/pip
SAMPLE_ENV_PYTHON := $(SAMPLE_ENV)/bin/python

TEST_ENV := $(IGNORE_DIRECTORY)/$(DISTRIBUTION_NAME)TestEnv
TEST_ENV_PYTHON := $(TEST_ENV)/bin/python
TEST_ENV_PIP := $(TEST_ENV)/bin/pip
TEST_ENV_NOSE := $(TEST_ENV)/bin/nosetests
TEST_ENV_SITE_PACKAGES := $(TEST_ENV)/lib/python2.7/site-packages

VIRTUALENV := virtualenv

DIST_DIR := dist/

DATA_DIR := data


ATLAS := $(DATA_DIR)/ASCENSION_ATLAS.png
ATLAS_META := $(DATA_DIR)/ASCENSION_ATLAS_META.json


dist: setup.py $(PYTHON_FILES) requirements.txt README MANIFEST.in MAKEFILE
	rm -f -r dist
	/usr/bin/env python setup.py sdist 

data:
	mkdir data

MAKE_SHORE_COMMAND = make_shore
MAKE_SHORE_SCRIPT = $(TOOL_DIR)/make_shore.py

.PHONY: shore
shore: $(MAKE_SHORE_SCRIPT)
	$(TEST_ENV_PYTHON) $(MANAGE_SCRIPT) $(MAKE_SHORE_COMMAND) $(GENERATED_TERRAIN_DIR)


MAKE_GRASSLAND_COMMAND = make_grassland
MAKE_GRASSLAND_SCRIPT = $(TOOL_DIR)/make_grassland.py

.PHONY: grassland
grassland: $(MAKE_GRASSLAND_SCRIPT)
	$(TEST_ENV_PYTHON) $(MANAGE_SCRIPT) $(MAKE_GRASSLAND_COMMAND) $(GENERATED_TERRAIN_DIR)


MAKE_FOREST_COMMAND = make_forest
MAKE_FOREST_SCRIPT = $(TOOL_DIR)/make_forest.py

.PHONY: forest
forest: $(MAKE_FOREST_SCRIPT)
	$(TEST_ENV_PYTHON) $(MANAGE_SCRIPT) $(MAKE_FOREST_COMMAND) $(GENERATED_TERRAIN_DIR)


MAKE_MOUNTAIN_COMMAND = make_mountain
MAKE_MOUNTAIN_SCRIPT = $(TOOL_DIR)/make_mountain.py

.PHONY: mountain
mountain: $(MAKE_MOUNTAIN_SCRIPT)
	$(TEST_ENV_PYTHON) $(MANAGE_SCRIPT) $(MAKE_MOUNTAIN_COMMAND) $(GENERATED_TERRAIN_DIR)


MAKE_SEA_COMMAND = make_sea
MAKE_SEA_SCRIPT = $(TOOL_DIR)/make_sea.py

.PHONY: sea 
sea: $(MAKE_SEA_SCRIPT)
	$(TEST_ENV_PYTHON) $(MANAGE_SCRIPT) $(MAKE_SEA_COMMAND) $(GENERATED_TERRAIN_DIR)


MAKE_ATLAS_COMMAND = make_atlas

.PHONY: atlas 
atlas: $(ATLAS) 
$(ATLAS): $(IMAGE_FILES) $(TOOL_SCRIPTS) data $(ANIMATION_META) $(MANAGE_SCRIPT) MAKEFILE
	$(TEST_ENV_PYTHON) $(MANAGE_SCRIPT) $(MAKE_ATLAS_COMMAND) $(IMAGE_DIR) \
		$(GENERATED_IMAGES_DIR)


.PHONY: sampleEnv
sampleEnv: $(SAMPLE_ENV)
$(SAMPLE_ENV): dist $(IGNORE_DIRECTORY)
	rm -f -r $(SAMPLE_ENV)
	$(VIRTUALENV) $(SAMPLE_ENV) --no-site-packages
	$(SAMPLE_ENV_PIP) install $(DIST_DIR)/$(DISTRIBUTION_NAME)*

.PHONY: testEnv
testEnv: $(TEST_ENV) 
$(TEST_ENV): requirements.txt MAKEFILE $(IGNORE_DIRECTORY)
	rm -f -r $(TEST_ENV)
	$(VIRTUALENV) $(TEST_ENV) --no-site-packages
	$(TEST_ENV_PIP) install -r requirements.txt
	$(TEST_ENV_PIP) install mock
	$(TEST_ENV_PIP) install unittest2
	$(TEST_ENV_PIP) install nose
	$(TEST_ENV_PIP) install nose-exclude

.PHONY: clean
clean:
	rm -f -r $(DISTRIBUTION_NAME).egg-info build dist MANIFEST $(SAMPLE_ENV) $(TEST_ENV) \
		$(ATLAS) $(ATLAS_META)

.PHONY: pyshell
pyshell: $(SAMPLE_ENV)
	$(SAMPLE_ENV_PYTHON)

.PHONY: test
test: $(TEST_ENV)
	$(TEST_ENV_NOSE) --exclude-dir=pyglet

.PHONY: debug
debug: $(TEST_ENV)
	$(TEST_ENV_NOSE) -s --exclude-dir=pyglet

$(IGNORE_DIRECTORY):
	mkdir $(IGNORE_DIRECTORY)
