"""

Script to initialize a working directory for patent processing. It does the
following things:

    (1) initialize the directory structure for the corpus,

    (2) import or create a file config/files.txt with all external files to
        process,

    (3) create a file config/pipeline-default.txt with default settings for the
        pipeline,

    (4) create a file config/general.txt with settings used by this script.


USAGE
   % python step1_initialize.py OPTIONS

OPTIONS
   --language en|de|cn      language, default is 'en'
   --filelist PATH          a file with a list of source files
   --source PATH            a directory with all the source files
   --corpus PATH            a directory where the corpus is initialized
   --shuffle                randomly sort config/files.txt, used with the
                             --source option

You must run this script from the directory it is in.

There are two typical invocations, one where a file list is given to
initialize the corpus and one where a source directory is given:

  % python step1_initialize.py \
      --language en \
      --corpus data/patents/test \
      --filelist filelist.txt

  % python step1_initialize.py \
      --language en \
      --corpus data/patents/test \
      --source ../external/US \
      --shuffle

Both commands create a directory data/patents/test, in which the corpus will be
initialized. It will include config/ and data/ subdirectories and several files
mentioned above in the config/ subdirectory. The first form copies filelist.txt
to en/config/files.txt. The second form traverses the directory ../external/US,
takes all file paths, randomly shuffles them, and then saves the result to
en/config/files.txt.

When the --filelist options is used, the system expects that FILE has two or
three columns with year, source file and an optional target file, which is the
filepath in the corpus starting at the target directory handed in with the
--corpus option. If there is no third column than the source and target file
will be the same as the source file, except that a leading path separator will
be stripped.

With the --source option, the source and target will always be the same and the
year will always be set to 0000. It is up to the user to change this if needed.


NOTES

Paths in config/general.txt can be either relative or absolute. Initially, all
settings are from this initialization script, but other configuration settings
could be added later.

The pipeline-default.txt file is tricky. It contains all default settings for
arguments handed over to individual components (tagger, chunker, maxent model
trainer etcetera). If more arguments are added, then this file should be updated
manually and it should then also be used to fill in default values for past
processing jobs (assuming that there is a default that makes sense).

The directory tree created inside the target directory is as follows:

    |-- config
    |   |-- files.txt
    |   |-- general.txt
    |   |-- pipeline-default.txt
    `-- data
        |-- d0_xml         'import of XML data'
        |-- d1_txt         'results of document structure parser'
        |-- d2_seg         'segmenter results'
        |-- d2_tag         'tagger results '
        |-- d3_phr_feats   'results from candidate selection'
        |-- o1_index       'term indexes'
        |-- o2_matcher     'results of the pattern matcher'
        |-- o3_selector    'results of the selector'
        |-- t0_annotate    'input for annotation effort'
        |-- t1_train       'vectors for the classifier and classifier models'
        |-- t2_classify    'classification results'
        |-- t3_test        'test and evaluation area'
        `-- workspace      'work space area'

Some of these directories are created for historical reasons and are not used
anymore. Also note that the processing stages are grouped using prefixes, where
the features carry some meaning:

   d -- document level processing
   t -- processing for the technology classifier
   o -- processing for the ontology creator (this is used by a downstream script)

No existing files or directories will be overwritten, except for the files in
the config directory that are listed above (general.txt, files.txt and
pipeline-default.txt).

"""


import os, sys, shutil, getopt, errno, random, time

import config, corpus


if __name__ == '__main__':

    options = ['language=', 'corpus=', 'filelist=', 'source=', 'shuffle']
    (opts, args) = getopt.getopt(sys.argv[1:], '', options)

    source_file = None
    source_path = None
    target_path = config.WORKING_PATENT_PATH
    language = config.LANGUAGE
    shuffle_file = False
    pipeline_config = config.DEFAULT_PIPELINE
    
    for opt, val in opts:
        if opt == '--language': language = val
        if opt == '--filelist': source_file = val
        if opt == '--source': source_path = val
        if opt == '--corpus': target_path = val
        if opt == '--shuffle': shuffle_file = True

    if language == 'cn':
            pipeline_config = config.DEFAULT_PIPELINE_CN

    corpus.Corpus(language, source_file, source_path,
                  target_path, pipeline_config, shuffle_file)
