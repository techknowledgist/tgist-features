"""

Module that contains corpus-level processing functionality. The Corpus class is
typically used by scripts that process files in batch.

"""

# TODO
#
# - Add option to grow an already initialized corpus. One question to answer here
#   is whether you just add lines to config/files.txt or also add some lines
#   saying that x files were added at time t.
#
# - The run_X methods all update the count in state/processed.txt every STEP
#   files. And at the end of each method, the final remainder is added and the
#   state/processing_history file is updated. We may want to update the history
#   with every STEP files as well and at the end get a final tally. Currently,
#   there is not guaranteed to be an entry when an error happens.
#
# - It might be a good idea to have a general way to catch exceptions for the
#   run_X methods. We could either have a try-except in each method or use a
#   with statement and a class for each run_X method. A superclass could deal
#   with errors and perhaps with bookkeeping to (instead of the decorator
#   function).
#
# - I do not really want to import sdp here, hide it in the segmenter code.
#
# - When populating a corpus, the code does not check whether there is anything
#   left to do. So if you have a corpus with 10 files and you do a --populate
#   with n=10, and you then do it again, then it will not complain, but it will
#   add a line to the state/processing-history.txt file.


import os, sys, shutil, getopt, errno, random, time, codecs

import xml2txt
import txt2tag
import sdp
import tag2chunk
import cn_txt2seg
import cn_seg2tag
import config

sys.path.append(os.path.abspath('../..'))
from utils.docstructure.main import Parser
from ontology.utils.file import ensure_path, get_file_paths, read_only
from ontology.utils.file import get_lines, compress, uncompress, get_year
from ontology.utils.git import get_git_commit
from ontology.utils.batch import RuntimeConfig, DataSet


# Names of processing stages
POPULATE = '--populate'
XML2TXT = '--xml2txt'
TXT2TAG = '--txt2tag'
TXT2SEG = '--txt2seg'
SEG2TAG = '--seg2tag'
TAG2CHK = '--tag2chk'

ALL_STAGES = [POPULATE, XML2TXT, TXT2TAG, TXT2SEG, SEG2TAG, TAG2CHK]

# definition of mappings from document processing stage to input and output data
# directories (named processing areas above)
DOCUMENT_PROCESSING_IO = \
    { POPULATE: { 'in': 'external', 'out': 'd0_xml' },
      XML2TXT: { 'in': 'd0_xml', 'out': 'd1_txt' },
      TXT2TAG: { 'in': 'd1_txt', 'out': 'd2_tag' },
      TXT2SEG: { 'in': 'd1_txt', 'out': 'd2_seg' },
      SEG2TAG: { 'in': 'd2_seg', 'out': 'd2_tag' },
      TAG2CHK: { 'in': 'd2_tag', 'out': 'd3_phr_feats' }}

# This variable governs after how many files the files_processed counter in the
# state directory is updated, this way we still have a reasonably recent count
# if there is an error that is not trapped.
STEP = 100

# Names of some standard files
FNAME_FILELIST = 'files.txt'
FNAME_INFO_GENERAL = 'general.txt'
FNAME_INFO_ADDITIONS = 'additions.txt'
FNAME_PIPELINE_DEFAULT = 'pipeline-default.txt'


def update_state(fun):
    """To be used as a decorator around functions that run one of the processing steps."""
    def wrapper(*args):
        t1 = time.time()
        files_processed, datasets = fun(*args)
        for dataset in datasets:
            dataset.files_processed += files_processed
            dataset.update_state(args[1], t1)
    return wrapper


@update_state
def run_populate(rconfig, limit, verbose=False):
    """Populate xml directory in the target directory with limit files from the
    source file list or the source directory."""

    output_name = DOCUMENT_PROCESSING_IO[POPULATE]['out']
    dataset = DataSet(POPULATE, output_name, rconfig)

    # initialize data set if it does not exist, this is not contingent on
    # anything because --populate is the first step
    if not dataset.exists():
        dataset.initialize_on_disk()
        dataset.load_from_disk()

    fspecs = get_lines(rconfig.filenames, dataset.files_processed, limit)
    print "[--populate] adding %d files to %s" % (len(fspecs), dataset)
    count = 0
    for fspec in fspecs:
        count += 1
        src_file = fspec.source
        dst_file = os.path.join(rconfig.target_path, 'data', output_name,
                                dataset.version_id, 'files', fspec.target)
        # allow for compressed files, while being handed the name without
        # extension
        if not os.path.exists(src_file):
            src_file += ".gz"
            dst_file += ".gz"
        if verbose:
            print "[--populate] %04d %s" % (count, dst_file)
        ensure_path(os.path.dirname(dst_file))
        shutil.copyfile(src_file, dst_file)
        # at some point there seemed to be an issue with compressing for Chinese,
        # so added this to do language dependent compressing, there is now no
        # difference for the population phase
        if rconfig.language == 'en': compress(dst_file)
        elif rconfig.language == 'cn': compress(dst_file)
        # TODO: does this mean that you miss some if total_count % STEP != 0
        if count % STEP == 0:
            dataset.update_processed_count(STEP)

    return (count % STEP, [dataset])


@update_state
def run_xml2txt(rconfig, limit, options, source, verbose=False):

    """Takes the xml file and produces a txt file with a simplified document
    structure, keeping date, title, abstract, summary, description_rest,
    first_claim and other_claims. Does this by calling the document structure
    parser in onto mode if the document source is LEXISNEXIS and uses a simple
    parser defined in xml2txt if the source is WOS.."""

    input_dataset = find_input_dataset(XML2TXT, rconfig)
    output_dataset = find_output_dataset(XML2TXT, rconfig)
    print_datasets(XML2TXT, input_dataset, output_dataset)
    check_file_counts(input_dataset, output_dataset, limit)

    count = 0
    doc_parser = make_parser(rconfig.language)
    workspace = os.path.join(rconfig.target_path, 'data', 'workspace')
    fspecs = get_lines(rconfig.filenames, output_dataset.files_processed, limit)
    for fspec in fspecs:
        count += 1
        filename = fspec.target
        print_file_progress(XML2TXT, rconfig.corpus, count, filename, verbose)
        file_in, file_out = prepare_io(filename, input_dataset, output_dataset)
        uncompress(file_in)
        try:
            xml2txt.xml2txt(doc_parser, source, file_in, file_out, workspace)
        except Exception as e:
            # just write an empty file that can be consumed downstream
            fh = codecs.open(file_out, 'w')
            fh.close()
            print "[--xml2txt] WARNING: error on", file_in
            print "           ", e
        # we do compress the cn output of the document parser
        if rconfig.language == 'en': compress(file_in, file_out)
        elif rconfig.language == 'cn': compress(file_in, file_out)
        if count % STEP == 0:
            output_dataset.update_processed_count(STEP)

    #xml2txt.print_stats()
    return (count % STEP, [output_dataset])


@update_state
def run_txt2tag(rconfig, limit, options, verbose):
    """Takes txt files and runs the tagger on them."""

    input_dataset = find_input_dataset(TXT2TAG, rconfig)
    output_dataset = find_output_dataset(TXT2TAG, rconfig)
    print_datasets(TXT2TAG, input_dataset, output_dataset)
    check_file_counts(input_dataset, output_dataset, limit)

    count = 0
    tagger = txt2tag.get_tagger(rconfig.language)
    fspecs = get_lines(rconfig.filenames, output_dataset.files_processed, limit)
    for fspec in fspecs:
        count += 1
        filename = fspec.target
        print_file_progress(TXT2TAG, rconfig.corpus, count, filename, verbose)
        file_in, file_out = prepare_io(filename, input_dataset, output_dataset)
        uncompress(file_in)
        txt2tag.tag(file_in, file_out, tagger)
        # this will become relevant for cn only when we have a segmenter/tagger
        # that uses only one step
        if rconfig.language == 'en': compress(file_in, file_out)
        if count % STEP == 0:
            output_dataset.update_processed_count(STEP)

    return (count % STEP, [output_dataset])


@update_state
def run_txt2seg(rconfig, limit, options, verbose):
    """Takes txt files and runs the Chinese segmenter on them."""

    input_dataset = find_input_dataset(TXT2SEG, rconfig)
    output_dataset = find_output_dataset(TXT2SEG, rconfig)
    print_datasets(TXT2SEG, input_dataset, output_dataset)
    check_file_counts(input_dataset, output_dataset, limit)

    count = 0
    segmenter = sdp.Segmenter()
    swrapper = cn_txt2seg.SegmenterWrapper(segmenter)

    fspecs = get_lines(rconfig.filenames, output_dataset.files_processed, limit)
    for fspec in fspecs:
        count += 1
        filename = fspec.target
        print_file_progress(TXT2SEG, rconfig.corpus, count, filename, verbose)
        file_in, file_out = prepare_io(filename, input_dataset, output_dataset)
        uncompress(file_in)
        #cn_txt2seg.seg(file_in, file_out, segmenter)
        swrapper.process(file_in, file_out)
        compress(file_in, file_out)
        if count % STEP == 0:
            output_dataset.update_processed_count(STEP)

    return (count % STEP, [output_dataset])


@update_state
def run_seg2tag(rconfig, limit, options, verbose):
    """Takes seg files and runs the Chinese tagger on them."""

    input_dataset = find_input_dataset(SEG2TAG, rconfig)
    output_dataset = find_output_dataset(SEG2TAG, rconfig)
    print_datasets(SEG2TAG, input_dataset, output_dataset)
    check_file_counts(input_dataset, output_dataset, limit)

    count = 0
    tagger = txt2tag.get_tagger(rconfig.language)
    fspecs = get_lines(rconfig.filenames, output_dataset.files_processed, limit)
    for fspec in fspecs:
        count += 1
        filename = fspec.target
        print_file_progress(SEG2TAG, rconfig.corpus, count, filename, verbose)
        file_in, file_out = prepare_io(filename, input_dataset, output_dataset)
        uncompress(file_in)
        cn_seg2tag.tag(file_in, file_out, tagger)
        compress(file_in, file_out)
        if count % STEP == 0:
            output_dataset.update_processed_count(STEP)

    return (count % STEP, [output_dataset])


@update_state
def run_tag2chk(rconfig, limit, options, verbose):
    """Runs the np-in-context code on tagged input. Populates d3_phr_feat."""

    candidate_filter = options.get('--candidate-filter', 'off')
    chunker_rules = options.get('--chunker-rules', 'en')

    # this is a hack that maps the value of the new official name to the value
    # expected by the old name
    filter_p = True if candidate_filter == 'on' else False
    
    input_dataset = find_input_dataset(TAG2CHK, rconfig)
    output_dataset = find_output_dataset(TAG2CHK, rconfig)
    print_datasets(TAG2CHK, input_dataset, output_dataset)
    print "[--tag2chk] using '%s' chunker rules" % chunker_rules
    check_file_counts(input_dataset, output_dataset, limit)

    count = 0
    fspecs = get_lines(rconfig.filenames, output_dataset.files_processed, limit)
    for fspec in fspecs:
        count += 1
        filename = fspec.target
        print_file_progress(TAG2CHK, rconfig.corpus, count, filename, verbose)
        file_in, file_out = prepare_io(filename, input_dataset, output_dataset)
        year = get_year(filename)
        tag2chunk.Doc(file_in, file_out, year, rconfig.language,
                      filter_p=filter_p, chunker_rules=chunker_rules, compress=True)
        if count % STEP == 0:
            output_dataset.update_processed_count(STEP)

    return (count % STEP, [output_dataset])



def find_input_dataset(stage, rconfig, data_type=None):
    """Find the input data set for a processing stage for a given configuration and return
    it. Print a warning and exit if no dataset or more than one dataset was found. If a
    data type is passed in, the dat type lookup for the stage is bypassed."""

    # Use the stage-to-data mapping to find the data_type if none was handed in
    if data_type is None:
        data_type = DOCUMENT_PROCESSING_IO[stage]['in']
    # Get all data sets D for input name
    dirname = os.path.join(rconfig.target_path, 'data', data_type)
    datasets1 = [ds for ds in os.listdir(dirname) if ds.isdigit()]
    datasets2 = [DataSet(stage, data_type, rconfig, ds) for ds in datasets1]
    # Filer the datasets making sure that d.trace + d.head matches
    # rconfig.pipeline(txt).trace
    datasets3 = [ds for ds in datasets2 if ds.input_matches_global_config()]
    # If there is one result, return it, otherwise write a warning and exit
    if len(datasets3) == 1:
        return datasets3[0]
    elif len(datasets3) > 1:
        print "WARNING, more than one approriate training set:"
        for ds in datasets3:
            print '  ', ds
        sys.exit("Exiting...")
    elif len(datasets3) == 0:
        print "WARNING: no datasets available to meet input requirements"
        sys.exit("Exiting...")

    
def find_output_dataset(stage, rconfig, data_type=None):
    """Find the output data set of a stage for a given configuration and return
    it. Print a warning and exit if no dataset or more than one dataset was
    found."""

    # Use the stage-to-data mapping to find the output names
    if data_type is None:
        data_type = DOCUMENT_PROCESSING_IO[stage]['out']
    #for output_name in data_types:
    # Get all data sets D for input name
    dirname = os.path.join(rconfig.target_path, 'data', data_type)
    datasets1 = [ds for ds in os.listdir(dirname) if ds.isdigit()]
    datasets2 = [DataSet(stage, data_type, rconfig, ds) for ds in datasets1]
    # Filer the datasets making sure that d.trace + d.head matches
    # rconfig.pipeline(txt).trace
    datasets3 = [ds for ds in datasets2 if ds.output_matches_global_config()]
    # If there is one result, return it, if there are more than one, write a
    # warning and exit, otherwise, initialize a dataset and return it
    if len(datasets3) == 1:
        return datasets3[0]
    elif len(datasets3) > 1:
        print "WARNING, more than one approriate training set found:"
        for ds in datasets3:
            print '  ', ds
        sys.exit("Exiting...")
    elif len(datasets3) == 0:
        highest_id = max([0] + [int(ds) for ds in datasets1])
        new_id = "%02d" % (highest_id + 1)
        dataset = DataSet(stage, data_type, rconfig, new_id)
        if not dataset.exists():
            dataset.initialize_on_disk()
            dataset.load_from_disk()
        print "[%s] created %s" % (stage, dataset)
        return dataset
    

def print_datasets(stage, input_dataset, output_dataset):
    print "[%s] input %s" % (stage, input_dataset)
    print "[%s] output %s" % (stage, output_dataset)

def print_file_progress(stage, corpus, count, filename, verbose):
    if verbose:
        print "[%s] %04d %s %s" % (stage, count, os.path.basename(corpus), filename)

def check_file_counts(input_dataset, output_dataset, limit):
    if input_dataset.files_processed < output_dataset.files_processed + limit:
        print "[check_file_counts] " + \
              "WARNING: input dataset does not have enough processed files"
        sys.exit("Exiting...")

def prepare_io(filename, input_dataset, output_dataset):
    """Generate the file paths for the datasets and make sure the path to the file exists for
    the output dataset. May need to add a version that deals with multiple output datasets."""
    file_id = filename[1:] if filename.startswith(os.sep) else filename
    file_in = os.path.join(input_dataset.path, 'files', file_id)
    file_out = os.path.join(output_dataset.path, 'files', file_id)
    ensure_path(os.path.dirname(file_out))
    return file_in, file_out

def make_parser(language):
    """Return a document structure parser for language."""
    parser = Parser()
    parser.onto_mode = True
    mappings = {'en': 'ENGLISH', 'de': "GERMAN", 'cn': "CHINESE" }
    parser.language = mappings[language]
    return parser


class Corpus(object):

    """Class that implements a corpus, where a corpus is understood to include
    all source documents as well as document-level processing on all documents
    in the corpus. This class gives access to corpus initialization as well as
    corpus-level batch processing of the corpus contents."""

    def __init__(self, language, source_file, source_path,
                 target_path, pipeline_config, shuffle_file):
        """Creates a directory named target_path and all subdirectories and
        files in there needed for further processing. See the module docstring
        in step1_initialize.py for more details."""
        self.language = language
        self.source_file = source_file
        self.source_path = source_path
        self.target_path = target_path
        self.pipeline_config = pipeline_config
        self.shuffle_file = shuffle_file
        self.data_path = os.path.join(self.target_path, 'data')
        self.conf_path = os.path.join(self.target_path, 'config')
        if self.source_file is not None or self.source_path is not None:
            self._initialize_directory()

    def _initialize_directory(self):
        self._generate_settings()
        if os.path.exists(self.target_path):
            sys.exit("WARNING: %s already exists, exiting" % self.target_path)
        self._print_initialize_message()
        self._create_directories()
        self._create_general_config_file()
        self._create_default_pipeline_config_file()
        self._create_filelist()
        print

    def _generate_settings(self):
        self.command = "$ python %s\n\n" % ' '.join(sys.argv)
        self.settings = ["timestamp    =  %s\n" % time.strftime("%x %X"),
                         "language     =  %s\n" % self.language,
                         "source_file  =  %s\n" % self.source_file,
                         "source_path  =  %s\n" % self.source_path,
                         "target_path  =  %s\n" % self.target_path,
                         "shuffle      =  %s\n" % str(self.shuffle_file),
                         "git_commit   =  %s\n" % get_git_commit()]

    def _print_initialize_message(self):
        print "\n[--init] initializing %s" % (self.target_path)
        print "\n   %s" % ("   ".join(self.settings))
    
    def _create_directories(self):
        """Create subdirectory structure in target_path."""
        print "[--init] creating directory structure in %s" % (self.target_path)
        ensure_path(self.conf_path)
        for subdir in config.PROCESSING_AREAS:
            subdir_path = self.data_path + os.sep + subdir
            ensure_path(subdir_path)

    def _create_filelist(self):
        """Create a list of files either by copying a given list or by traversing a
        given directory."""
        print "[--init] creating %s/%s" % (self.conf_path, FNAME_FILELIST)
        file_list = os.path.join(self.conf_path, FNAME_FILELIST)
        if self.source_file is not None:
            shutil.copyfile(self.source_file, file_list)
        elif self.source_path is not None:
            filenames = get_file_paths(self.source_path)
            if self.shuffle_file:
                random.shuffle(filenames)
            with open(file_list, 'w') as fh:
                for fname in filenames:
                    fh.write("0000\t" + fname + "\n")
        else:
            sys.exit("[--init] ERROR: " +
                     "need to define input with --filelist or " +
                     "--source-directory option, aborting")
        read_only(file_list)

    def _create_general_config_file(self):
        filename = os.path.join(self.conf_path, FNAME_INFO_GENERAL)
        print "[--init] creating %s" % (filename)
        fh = open(filename, 'w')
        fh.write(self.command)
        fh.write("".join(self.settings))
        read_only(filename)

    def _create_default_pipeline_config_file(self):
        filename = os.path.join(self.conf_path, FNAME_PIPELINE_DEFAULT)
        print "[--init] creating %s" % (filename)
        fh = open(filename, 'w')
        fh.write(self.pipeline_config.lstrip())
        read_only(filename)

    def populate(self, rconfig, limit, verbose):
        run_populate(rconfig, limit, verbose)
        if verbose: print

    def xml2txt(self, rconfig, limit, options, source, verbose):
        run_xml2txt(rconfig, limit, options, source, verbose)
        if verbose: print

    def txt2tag(self, rconfig, limit, options, verbose):
        run_txt2tag(rconfig, limit, options, verbose)
        if verbose: print

    def txt2seg(self, rconfig, limit, options, verbose):
        run_txt2seg(rconfig, limit, options, verbose)
        if verbose: print

    def seg2tag(self, rconfig, limit, options, verbose):
        run_seg2tag(rconfig, limit, options, verbose)
        if verbose: print

    def tag2chk(self, rconfig, limit, options, verbose):
        run_tag2chk(rconfig, limit, options, verbose)
        if verbose: print
