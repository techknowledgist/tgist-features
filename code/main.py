"""main.py

Script to process all documents in a file list and create an annotated
corpus. Will initialize the corpus directory, add the source data from the file
list and add results from the document structure parser, the tagger and the
feature extractor. This script combines what is done in the step1_init.py and
step2_process.py scripts, but it simplifies the process a bit.

Use this script when running on a small number fo documents, say a couple of
hundred or less depending on the size. For larger jobs, use step1_init.py and
step2_process.py.

USAGE
   % python main.py OPTIONS

OPTIONS
   --language en|cn       language, default is 'en'
   --source ln|wos|cnki   data source, default is 'ln'
   --filelist PATH        a file with a list of source files
   --corpus PATH          a directory where the corpus is created
   --verbose              print more verbose information
   --overwrite            overwrite existing corpus

You must run this script from the directory it is in.

Typical invocation:

   % python main.py --corpus patents-test --filelist filelist.txt
   % python main.py --corpus test --filelist ../data/lists/sample-us.txt

This creates a directory test, in which the corpus will be initialized. The
directory will include config/ and data/ subdirectories and several files in the
config/ subdirectory. The script copies sample-us.txt to config/files.txt so
there is always a local copy of the list with all input files. Note that the -n
option is not given and therefore all documents will be processed.

For the --filelist option, the system expects that FILE has two or three
tab-separated columns with year, source file and an optional target file, which
can be used to simplify and flatten the directory structure. For example, the
three columns in a line of the file list could be:

    1980   /data/patents/1980/US4192770A.xml   1980/US4192770A.xml

In this case, the source file (second column) will be copied to a local path
1980/US4192770A.xml inside the corpus. If there is no third column than the path
of the source file will be copied into the corpus directory in its entirety.

The directory tree created inside the test directory is as follows:

    |-- config
    |   |-- files.txt
    |   |-- general.txt
    |   `-- pipeline-default.txt
    `-- data
        |-- d0_xml     'import of XML data'
        |-- d1_txt     'results of document structure parser'
        |-- d2_seg     'segmenter results'
        |-- d2_tag     'tagger results '
        |-- d3_feats   'results from candidate selection and feature extraction'
        `-- workspace  'work space area'

The script performs document-level processing and fills in d0_xml, d1_txt,
d2_seg (Chinese only), d2_tag and d3_feats. The structures of those directories
mirror each other and look as follows:

    `-- 01
        |-- state
        |   |-- processed.txt
        |   `-- processing-history.txt
        |-- config
        |   |-- pipeline-head.txt
        |   `-- pipeline-trace.txt
        `-- files
            |-- 1980
            |   |-- US4246708A.xml.gz
            |   `-- US4254395A.xml.gz
            `-- 1981
                |-- US4236596A.xml.gz
                `-- US4192770A.xml.gz

All files are compressed. The first part of the directory tree is a run
identifier, almost always '01' unless the corpus was processed in different
ways (using different chunker rules for example). As mentioned above, the
structure under the files directory is determined by the third column in the
file list.

There are two options that allow you to specify the location of the Stanford
tagger and segmenter.

--stanford-tagger-dir PATH
--stanford-segmenter-dir PATH
   These can be used to overrule the default directories for the Stanford
   segmenter and tagger as defined in config.py.

"""


import sys, getopt, shutil

import config
from corpus import Corpus
from utils.batch import RuntimeConfig


def process_corpus(language, source, filelist, corpus_location, verbose):
    """Create a corpus at corpus_location and run the default pipeline over it."""
    pipeline = config.DEFAULT_PIPELINE
    if language == 'cn':
        pipeline = config.DEFAULT_PIPELINE_CN
    pipeline_file = config.DEFAULT_PIPELINE_CONFIGURATION_FILE
    corpus = Corpus(language=language, datasource=source, source_file=filelist,
                    corpus_path=corpus_location, pipeline_config=pipeline)
    rconfig = RuntimeConfig(corpus_location, language, source, pipeline_file,
                            verbose=verbose)
    corpus.run_default_pipeline(rconfig)


if __name__ == '__main__':

    options = ['language=', 'data=', 'corpus=', 'filelist=', 'verbose', 'overwrite',
               'stanford-segmenter-dir=', 'stanford-tagger-dir=']
    (opts, args) = getopt.getopt(sys.argv[1:], 'l:d:f:c:', options)

    opt_overwrite = False
    opt_filelist = None
    opt_corpus = None
    opt_verbose = False
    opt_language = config.LANGUAGE
    opt_source = config.DATASOURCE

    for opt, val in opts:
        if opt in ('-l', '--language'): opt_language = val
        if opt in ('-d', '--source'): opt_source = val
        if opt in ('-f', '--filelist'): opt_filelist = val
        if opt in ('-c', '--corpus'): opt_corpus = val
        if opt == '--verbose': opt_verbose = True
        if opt == '--overwrite': opt_overwrite = True
        if opt == '--stanford-segmenter-dir': config.update_stanford_segmenter(val)
        if opt == '--stanford-tagger-dir': config.update_stanford_tagger(val)

    config.check_stanford_tagger()
    config.check_stanford_segmenter()
    if opt_overwrite:
        shutil.rmtree(opt_corpus)
    if opt_filelist is None:
        exit("ERROR: missing -f or --filelist option")
    if opt_corpus is None:
        exit("ERROR: missing -c or --corpus option")

    process_corpus(opt_language, opt_source, opt_filelist, opt_corpus, opt_verbose)
