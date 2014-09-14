"""

Script that manages the part of the processing chain that deals with individual documents,
that is document parsing, segmentation, tagging, chunking and creation of phrase-level and
document-level feature vectors.

USAGE:
  % python step2_document_processing.py OPTIONS

OPTIONS:
  --populate   import external files
  --xml2txt    document structure parsing
  --txt2tag    tagging (English and German)
  --txt2seg    segmenting (Chinese only)
  --seg2tag    tagging segemented text (Chinese only)
  --tag2chk    creating chunks in context and adding features

  --corpus TARGET_PATH  corpus directory, default is data/patents
  -l en|cn|de          provides the language, default is 'en'
  -n INTEGER           number of documents to process, default is 1

  --verbose:
       print name of each processed file to stdout

  --show-data:
       print all datasets, then exits, requires the -t option
       if --verbose is used, will also print the pipelines for each dataset

  --show-pipeline
       print all pipelines, then exits, requires the -t option, also assumes
       that all pipeline files match 'pipeline-*.txt'

  --show-processing-time
       show processing time for the corpus

  --pipeline FILE:
      optional pipeline configuration file to overrule the default pipeline; this is just
      the basename not path, so with '--pipeline conf.txt', the config file loaded is
      TARGET_PATH/LANGUAGE/config/conf.txt
                              
The script assumes an initialized directory (created with step1_initialize.py)
with a set of external files defined in TARGET_PATH/config/files.txt. Default
pipeline configuration settings are in TARGET_PATH/config/pipeline-default.txt.

Examples:
   %  python step2_document_processing.py --corpus data/patents/en --populate -n 5
   %  python step2_document_processing.py --corpus data/patents/en --xml2txt -n 5
   %  python step2_document_processing.py --corpus data/patents/en --txt2tag -n 5
   %  python step2_document_processing.py --corpus data/patents/en --tag2chk -n 5

"""


import os, sys, getopt

import config
from corpus import Corpus
from corpus import POPULATE, XML2TXT, TXT2TAG, TXT2SEG, SEG2TAG, TAG2CHK
from corpus import ALL_STAGES

sys.path.append(os.path.abspath('../..'))
from ontology.utils.batch import RuntimeConfig
from ontology.utils.batch import show_datasets, show_pipelines
from ontology.utils.batch import show_processing_time


def read_opts():
    options = ['corpus=', 'source=', 'populate',
               'xml2txt', 'txt2tag', 'txt2seg', 'seg2tag', 'tag2chk',
               'verbose', 'pipeline=', 'show-data', 'show-pipelines',
               'show-processing-time']
    try:
        return getopt.getopt(sys.argv[1:], 'l:n:', options)
    except getopt.GetoptError as e:
        sys.exit("ERROR: " + str(e))

        
if __name__ == '__main__':

    # default values of options
    corpus_path = config.WORKING_PATENT_PATH
    source = 'LEXISNEXIS'
    language = config.LANGUAGE
    stage = None
    pipeline_config = 'pipeline-default.txt'
    verbose, show_data_p, show_pipelines_p = False, False, False
    show_processing_time_p = False
    limit = 1
    
    (opts, args) = read_opts()
    for opt, val in opts:
        if opt == '--corpus': corpus_path = val
        if opt == '--source': source = val
        if opt == '-l': language = val
        if opt == '-n': limit = int(val)
        if opt == '--verbose': verbose = True
        if opt == '--pipeline': pipeline_config = val
        if opt == '--show-data': show_data_p = True
        if opt == '--show-pipelines': show_pipelines_p = True
        if opt == '--show-processing-time': show_processing_time_p = True
        if opt in ALL_STAGES:
            stage = opt

    # NOTE: this is named rconfig to avoid confusion with config.py
    rconfig = RuntimeConfig(corpus_path, None, None, language, pipeline_config)
    #rconfig.pp()

    if show_data_p:
        show_datasets(rconfig, config.DATA_TYPES, verbose)
        exit()
    if show_pipelines_p:
        show_pipelines(rconfig)
    if show_processing_time_p:
        show_processing_time(rconfig, config.DATA_TYPES)
        exit()

    # note that the second argument always has to be the limit, this is required
    # by update_state()
    options = rconfig.get_options(stage)

    # corpus already exists in a directory, so not all arguments are needed
    corpus = Corpus(None, None, None, corpus_path, None, None)

    if stage == POPULATE:
        corpus.populate(rconfig, limit, verbose)
    elif stage == XML2TXT:
        corpus.xml2txt(rconfig, limit, options, source, verbose)
    elif stage == TXT2TAG:
        corpus.txt2tag(rconfig, limit, options, verbose)
    elif stage == TXT2SEG:
        corpus.txt2seg(rconfig, limit, options, verbose)
    elif stage == SEG2TAG:
        corpus.seg2tag(rconfig, limit, options, verbose)
    elif stage == TAG2CHK:
        corpus.tag2chk(rconfig, limit, options, verbose)
