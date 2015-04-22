DISTRIBUTION_NAME := ascension
IGNORE_DIRECTORY := ignore

TOOL_DIR := tools
IMAGE_DIR := images

PYTHON_FILES = $(shell find . -name \*.py -not -path "./$(TOOL_DIR)/*" -not -path \
               "./$(TOOL_DIR)/*" -not -path "./test/*" -not -name setup.py)
TOOL_SCRIPTS = $(shell find $(TOOL_DIR) -name \*.py)
IMAGE_FILES = $(shell find $(IMAGE_DIR) -name \*.png)

SAMPLE_ENV := $(IGNORE_DIRECTORY)/$(DISTRIBUTION_NAME)SampleEnv
SAMPLE_ENV_PIP := $(SAMPLE_ENV)/bin/pip
SAMPLE_ENV_PYTHON := $(SAMPLE_ENV)/bin/python

TEST_ENV := $(IGNORE_DIRECTORY)/$(DISTRIBUTION_NAME)TestEnv
TEST_ENV_PYTHON := $(TEST_ENV)/bin/python
TEST_ENV_PYTHON_64 := $(TEST_ENV)/bin/python-64
TEST_ENV_PIP := $(TEST_ENV)/bin/pip
TEST_ENV_NOSE := $(TEST_ENV)/bin/nosetests
TEST_ENV_SITE_PACKAGES := $(TEST_ENV)/lib/python2.7/site-packages

VIRTUALENV := virtualenv

PYGAME := $(shell echo $(PYGAME))

DIST_DIR := dist/

DATA_DIR := data


ATLAS := $(DATA_DIR)/ASCENSION_ATLAS.png
ATLAS_META := $(DATA_DIR)/ASCENSION_ATLAS_META.json

dist: setup.py $(PYTHON_FILES) requirements.txt README MANIFEST.in MAKEFILE
	rm -f -r dist
	/usr/bin/env python setup.py sdist 

.PHONY: atlas 
atlas: $(ATLAS)
$(ATLAS): $(IMAGE_FILES) $(TOOL_SCRIPTS)
	$(TEST_ENV_PYTHON) $(TOOL_DIR)/make_atlas.py $(IMAGE_DIR)

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
	# mv $(TEST_ENV_PYTHON) $(TEST_ENV_PYTHON_64)
	#lipo -remove x86_64 $(TEST_ENV_PYTHON_64) -output $(TEST_ENV_PYTHON)
	ln -s $(PYGAME) $(TEST_ENV_SITE_PACKAGES)/pygame
	$(TEST_ENV_PIP) install -r requirements.txt
	$(TEST_ENV_PIP) install mock
	$(TEST_ENV_PIP) install unittest2
	$(TEST_ENV_PIP) install nose

.PHONY: clean
clean:
	rm -f -r $(DISTRIBUTION_NAME).egg-info build dist MANIFEST $(SAMPLE_ENV) $(TEST_ENV) \
		$(ATLAS) $(ATLAS_META)

.PHONY: pyshell
pyshell: $(SAMPLE_ENV)
	$(SAMPLE_ENV_PYTHON)

.PHONY: test
test: $(TEST_ENV)
	$(TEST_ENV_NOSE)

.PHONY: debug
debug: $(TEST_ENV)
	$(TEST_ENV_NOSE) -s

$(IGNORE_DIRECTORY):
	mkdir $(IGNORE_DIRECTORY)
