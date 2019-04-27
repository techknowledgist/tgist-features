"""

File with configuration settings. Used all caps for all variables that are
intended to be consumed by other scripts.

Configuration settings in this file:

- general settings
- processing pipeline
- stanford tool locations and settings

One of the things that this script does is to calculate some default settings
for where the Stanford tagger and segmenter live, using some idiosyncracies of
the setup on several laptops and desktops and on Fusenet.

These settings can be overruled by using command line options for the main.py
script.

"""

import os, sys


### General settings
### -----------------------------------------------------------------------

# default language
LANGUAGE = "en"

# default data source
DATASOURCE = 'ln'

# directory with resources
RESOURCES = "resources"


### Pipeline settings
### -----------------------------------------------------------------------

# definition of default configuration file and the default pipeline
# configurations

DEFAULT_PIPELINE_CONFIGURATION_FILE = 'pipeline-default.txt'

DEFAULT_PIPELINE = """
# This file contains the default pipeline configuration settings. Settings in
# here can be overruled by handing the step2_process.py script the identifier
# for another configuration file. All pipeline configuration files live inside
# of the config directory configuration file.

--populate
--xml2txt
--txt2tag
--tag2chk --candidate-filter=off --chunker-rules=en
"""

DEFAULT_PIPELINE_CN = """
# This file contains the default pipeline configuration settings for Chinese. Settings in
# here can be overruled by handing the step2_document_processing script the identifier for
# another configuration file. All pipeline configuration files live inside of the config
# directory configuration file.

--populate
--xml2txt
--txt2seg
--seg2tag
--tag2chk --candidate-filter=off --chunker-rules=cn
"""

# Definition of sub directory names for processing stages.

DATA_DIRS = ['d0_xml', 'd1_txt', 'd2_seg', 'd2_tag', 'd3_feats', 'workspace']



### Stanford parser/segmenter settings
### -----------------------------------------------------------------------

# Locations for the tagger and the segmenter, default is to look into the tools
# directory for the 2012-07-09 version

STANFORD_TAGGER_DIR = os.path.join('tools', "stanford-postagger-full-2012-07-09" )
STANFORD_SEGMENTER_DIR = os.path.join('tools', "stanford-segmenter-2012-07-09")


# memory use for the stanford tagger and segmenter
STANFORD_MX = "2000m"

STANFORD_DEBUG_P = 1

STANFORD_SENTENCES = "newline"

# parameters for 3 kinds of output, the output format variable does not appear to be used
STANFORD_TAG_SEPARATOR = "_"
STANFORD_TOKENIZED = 0
STANFORD_OUTPUT_FORMAT = "wordsAndTags"
#STANFORD_OUTPUT_FORMAT = "wordsAndTags,penn,typedDependenciesCollapsed"

### use these parameters to test handling of pre-tagged input
# if tokenized = 1 and tag_separator = "/"
# then parser should use tags provided in input line
# tag_separator = "/"
# tokenized = 1
# output_format = "penn,typedDependenciesCollapsed"


# Some utilities for updating and checking tool directories

def update_stanford_tagger(path):
    """Method to update the path to the Stanford tagger."""
    global STANFORD_TAGGER_DIR
    STANFORD_TAGGER_DIR = path

def update_stanford_segmenter(path):
    """Method to update the path to the Stanford segmenter."""
    global STANFORD_SEGMENTER_DIR
    STANFORD_SEGMENTER_DIR = path
    check_directory(STANFORD_SEGMENTER_DIR)

def check_stanford_tagger():
    #global STANFORD_TAGGER_DIR
    check_directory(STANFORD_TAGGER_DIR)

def check_stanford_segmenter():
    check_directory(STANFORD_SEGMENTER_DIR)

def check_directory(path):
    """Check whether path exists and whether it has spaces. The latter is needed
    because calling the tagger causes a nasty loop and the code hangs if we hand
    in a path with spaces. Exit with an error message if a problem was found."""
    if not os.path.isdir(path):
        exit("ERROR - path does not exist: %s" % path)
    if path.find(' ') > -1:
        exit("ERROR - path contains spaces: %s" % path)
