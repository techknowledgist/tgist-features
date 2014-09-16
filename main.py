"""

Script to process all documents in a corpus. Will initialize the corpus
directory if needed. Combines what is done in the step1_initialize.py and
step2_document_processing.py, but simplifies the process a bit.

USAGE
   % python main.py OPTIONS

OPTIONS
   --language en|cn      language, default is 'en'
   --filelist PATH       a file with a list of source files
   --corpus PATH         a directory where the corpus is created
   -n INTEGER            number of files to process, defaults to all files
   
You must run this script from the directory it is in.

Typical invocation:

   % python main.py \
       --language en \
       --corpus data/patents/test \
       --filelist filelist.txt

This creates a directory data/patents/test, in which the corpus will be
initialized. The directory will include config/ and data/ subdirectories and
several files in the config/ subdirectory. The script copies filelist.txt to
en/config/files.txt so there is always a local copy of the list with all input
files. Note that the -n option is not given and therefore all documents will be
processed.

For the --filelist option, the system expects that FILE has two or three
tab-separated columns with year, source file and an optional target file, which
can be used to simplify and flatten the directory structure. For example, the
three columns in a line of the file list could be:

    1980
    /data/500-patents/DATA/Lexis-Nexis/US/Xml/1980/US4192770A.xml
    1980/US4192770A.xml

In this case, the source file (second column) will be copied to a local path
1980/US4192770A.xml inside the corpus. If there is no third column than the path
of the source file will be copied into the corpus directory.

The directory tree created inside the target directory is as follows:

    |-- config
    |   |-- files.txt
    |   |-- general.txt
    |   `-- pipeline-default.txt
    `-- data
        |-- d0_xml         'import of XML data'
        |-- d1_txt         'results of document structure parser'
        |-- d2_seg         'segmenter results'
        |-- d2_tag         'tagger results '
        |-- d3_phr_feats   'results from candidate selection and feature extraction'
        |-- o1_index       'term indexes'
        |-- o2_matcher     'results of the pattern matcher'
        |-- o3_selector    'results of the selector'
        |-- t0_annotate    'input for annotation effort'
        |-- t1_train       'vectors for the classifier and classifier models'
        |-- t2_classify    'classification results'
        |-- t3_test        'test and evaluation area'
        `-- workspace      'work space area'

This script only performs document-level processing and fills in d0_xml, d1_txt,
d2_seg (Chinese only), d2_tag and d3_phr_feats. The structure of those
directories mirror each other and look as follows (this example only has two
files listed):

    `-- 01
        |-- state
        |   |-- processed.txt
        |   `-- processing-history.txt
        |-- config
        |   |-- pipeline-head.txt
        |   `-- pipeline-trace.txt
        `-- files
            |-- 1985
            |   ` US4523055A.xml.gz
            `-- 1986
                ` US4577022A.xml.gz

All files are compressed. The first part of the directory tree is a run
identifier, usually always '01' unless the corpus was processed in different
ways (using different chunker rules for example). As mentioned above, the
structure under the files directory is determined by the third column in the
file list.

There are two options that allow you to specifiy the location of the Stanford
tagger and segmenter.

--stanford-tagger-dir PATH
--stanford-segmenter-dir PATH
   These can be used to overrule the default directories for the Stanford
   segmenter and tagger.

"""


import os, sys, getopt

import config
from corpus import Corpus
from corpus import POPULATE, XML2TXT, TXT2TAG, TXT2SEG, SEG2TAG, TAG2CHK
from ontology.utils.batch import RuntimeConfig


def update_stanford_tagger(path):
    if os.path.isdir(path):
        config.STANFORD_TAGGER_DIR = path
    else:
        print "WARNING: invalid path specified for STANFORD_TAGGER_DIR"

def update_stanford_segmenter(path):
    if os.path.isdir(path):
        config.STANFORD_SEGMENTER_DIR = path
    else:
        print "WARNING: invalid path specified for STANFORD_SEGMENTER_DIR"


if __name__ == '__main__':

    options = ['language=', 'corpus=', 'filelist=', 'verbose',
               'stanford-segmenter-dir=', 'stanford-tagger-dir=']
    (opts, args) = getopt.getopt(sys.argv[1:], 'l:f:c:n:v', options)

    source_file = None
    corpus_path = None
    verbose = False
    language = config.LANGUAGE
    source = 'LEXISNEXIS'
    limit = None

    for opt, val in opts:
        if opt in ('-l', '--language'): language = val
        if opt in ('-f', '--filelist'): source_file = val
        if opt in ('-c', '--corpus'): corpus_path = val
        if opt in ('-v', '--verbose'): verbose = True
        if opt == '-n': limit = int(val)
        if opt == '--stanford-segmenter-dir': update_stanford_segmenter(val)
        if opt == '--stanford-tagger-dir': update_stanford_tagger(val)

    pipeline = config.DEFAULT_PIPELINE
    pipeline_file = 'pipeline-default.txt'
    if language == 'cn':
        pipeline = config.DEFAULT_PIPELINE_CN

    if source_file is None: exit("ERROR: missing -f or --filelist option")
    if corpus_path is None: exit("ERROR: missing -c or --corpus option")

    c = Corpus(language, source_file, None, corpus_path, pipeline, None)
    rconfig = RuntimeConfig(corpus_path, None, None, language, pipeline_file)
    if limit is None:
        limit = len([f for f in open(rconfig.filenames).readlines() if len(f.split()) > 1])

    c.populate(rconfig, limit, verbose)
    c.xml2txt(rconfig, limit, {}, source, verbose)
    if language == 'en':
        c.txt2tag(rconfig, limit, {}, verbose)
    elif language == 'cn':
        c.txt2seg(rconfig, limit, {}, verbose)
        c.seg2tag(rconfig, limit, {}, verbose)
    c.tag2chk(rconfig, limit, {}, verbose)

