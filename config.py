"""

File with configuration settings. Intended to replace all previous configuration
files, which were named inconsistently and which duplicated some code. Used all
caps for all variables that are intended to be consumed by other scripts.

Configuration settings in this file:
- general settings
- processing pipeline
- stanford tool locations and settings
- settings for pipeline and patent_analyzer scripts

One of the things that this script does is to calculate some default settings
for where the Stanford tagger and segmenter live, using some idiosyncracies of
the setup on several laptops and desktops and on Fusenet.

These settings can be overruled by using command line options for the main.py
script. Something similar needs to be done for step2_document_processing.py, but
that is less urgent because non-Brandeis users will probably always use main.py.

"""

import os, sys


# First some code to determine what machine we are running this on, will be used
# to determine default locations for the Stanford tools.

script_path = os.path.abspath(sys.argv[0])
if script_path.startswith('/shared/home'):
    location = 'FUSENET'
elif script_path.startswith('/home/j/'):
    location = 'BRANDEIS'
elif script_path.startswith('/local/chalciope/'):
    location = 'BRANDEIS'
elif script_path.startswith('/Users/'): 
    location = 'MAC'
else:
    #print "WARNING: could not determine the location"
    location = None


### General settings
### -----------------------------------------------------------------------

# default language
LANGUAGE = "en"

# default data source
DATASOURCE = 'ln'

# annotations directory, general and for the language
ANNOTATION_DIRECTORY = "../annotation"
ANNOT_LANG_PATH = ANNOTATION_DIRECTORY + "/" + LANGUAGE


### Pipeline settings
### -----------------------------------------------------------------------

# definition of default configuration file and the default pipeline
# configurations

DEFAULT_PIPELINE_CONFIGURATION_FILE = 'pipeline-default.txt'

DEFAULT_PIPELINE = """
# This file contains the default pipeline configuration settings. Settings in
# here can be overruled by handing the step2_document_processing script the
# identifier for another configuration file. All pipeline configuration files
# live inside of the config directory configuration file.

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

# Definition of sub directory names for processing stages. DATA_TYPES is also
# defined in ../classifier, if it is changed here it should be changed there as
# well. (TODO: remove this dependency)

DATA_TYPES = \
    ['d0_xml', 'd1_txt', 'd2_seg', 'd2_tag', 'd3_phr_feats']
PROCESSING_AREAS = \
    DATA_TYPES + ['t0_annotate', 't1_train', 't2_classify', 't3_test',
                  'o1_index', 'o2_matcher', 'o3_selector', 'workspace' ]


### Stanford parser/segmenter settings
### -----------------------------------------------------------------------

STANFORD_TAGGER_RELEASE = "2012-07-09"
STANFORD_SEGMENTER_RELEASE = "2012-07-09"

# tagger and segmenter location
if location == 'BRANDEIS':
    base_dir = "/home/j/corpuswork/fuse/code/patent-classifier/tools/stanford/"
    STANFORD_TAGGER_DIR = base_dir + "stanford-postagger-full-2012-07-09" 
    STANFORD_SEGMENTER_DIR = base_dir + "stanford-segmenter-2012-07-09"
elif location == 'FUSENET':
    # the tools are at both spots, but the former is on a partition with less
    # space so may be removed
    base_dir = "/home/fuse/tools/"
    base_dir = "/shared/home/marc/tools/"
    STANFORD_TAGGER_DIR = base_dir + "stanford-postagger-full-2012-07-09"
    STANFORD_SEGMENTER_DIR = base_dir + "stanford-segmenter-2012-07-09"
elif location == 'MAC':
    base_dir = '/Applications/ADDED/nlp/stanford/'
    STANFORD_TAGGER_DIR = base_dir + "stanford-postagger-full-2012-07-09"
    STANFORD_SEGMENTER_DIR = base_dir + "stanford-segmenter-2012-07-09"
else:
    # cobbel together a path local to the repository
    tools_path = os.path.join(script_path, '..', '..', 'tools')
    tools_path = os.path.abspath(tools_path)
    STANFORD_TAGGER_DIR = os.path.join(tools_path, "stanford-postagger-full-2012-07-09" )
    STANFORD_SEGMENTER_DIR = os.path.join(tools_path, "stanford-segmenter-2012-07-09")

def update_stanford_tagger(path):
    """Method to update the path to the Stanford tagger."""
    if os.path.isdir(path):
        config.STANFORD_TAGGER_DIR = path
    else:
        print "WARNING: invalid path specified for STANFORD_TAGGER_DIR"

def update_stanford_segmenter(path):
    """Method to update the path to the Stanford segmenter."""
    if os.path.isdir(path):
        config.STANFORD_SEGMENTER_DIR = path
    else:
        print "WARNING: invalid path specified for STANFORD_SEGMENTER_DIR"

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

# See discarded/sdp_config for Some older settings that are not used anymore
