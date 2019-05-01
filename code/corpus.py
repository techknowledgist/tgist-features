"""

Module that contains corpus-level processing functionality. The Corpus class is
typically used by scripts that process files in batch.

"""

# TODO
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
# - When populating a corpus, the code does not check whether there is anything
#   left to do. So if you have a corpus with 10 files and you do a --populate
#   with n=10, and you then do it again, then it will not complain, but it will
#   add a line to the state/processing-history.txt file.


import os, sys, shutil, random, time, codecs

import xml2txt
import txt2tag
import tag2chunk
import cn_txt2seg
import cn_seg2tag
import config

from docstructure.main import Parser
from utils.path import ensure_path, get_file_paths, read_only, open_input_file
from utils.path import compress, uncompress
from utils.git import get_git_commit
from utils.batch import DataSet


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
    {POPULATE: {'in': 'external', 'out': 'd0_xml'},
     XML2TXT: {'in': 'd0_xml', 'out': 'd1_txt'},
     TXT2TAG: {'in': 'd1_txt', 'out': 'd2_tag'},
     TXT2SEG: {'in': 'd1_txt', 'out': 'd2_seg'},
     SEG2TAG: {'in': 'd2_seg', 'out': 'd2_tag'},
     TAG2CHK: {'in': 'd2_tag', 'out': 'd3_feats'}}

# This variable governs after how many files the files_processed counter in the
# state directory is updated, this way we still have a reasonably recent count
# if there is an error that is not trapped.
STEP = 100


# Names of some standard files
FNAME_FILELIST = 'files.txt'
FNAME_INFO_GENERAL = 'general.txt'
FNAME_INFO_ADDITIONS = 'additions.txt'
FNAME_PIPELINE_DEFAULT = 'pipeline-default.txt'


class Corpus(object):

    """Class that implements a corpus, where a corpus is understood to include
    all source documents as well as document-level processing on all documents
    in the corpus. This class gives access to corpus initialization as well as
    corpus-level batch processing of the corpus contents."""

    def __init__(self, language='en', datasource=None,
                 source_file=None, source_path=None, corpus_path=None,
                 pipeline_config=None, shuffle_file=False):
        """Create the corpus object which keeps information about path, pipeline,
        language, datasource and local file paths. Initialize directories on
        disk if there is a source_file or source_path argument that is not None,
        otherwise this will create an empty in-memory corpus."""
        self.location = corpus_path
        self.language = language
        self.datasource = datasource
        self.source_file = source_file
        self.source_path = source_path
        self.pipeline_config = pipeline_config
        self.shuffle_file = shuffle_file
        self.data_path = os.path.join(self.location, 'data')
        self.conf_path = os.path.join(self.location, 'config')
        self.file_list = os.path.join(self.conf_path, FNAME_FILELIST)
        if self.source_file is not None or self.source_path is not None:
            self._initialize_directory()

    def __str__(self):
        return "<Corpus '%s'>" % self.location \
            + "\n   source_file = %s" % self.source_file \
            + "\n   source_path = %s" % self.source_path \
            + "\n   language = %s" % self.language \
            + "\n   datasource = %s" % self.datasource

    def _initialize_directory(self):
        """Creates a directory named self.location and all subdirectories and 
        files in there that are needed for further processing. See the module
        docstring in step1_init.py for more details."""
        if os.path.exists(self.location):
            sys.exit("WARNING: %s already exists, exiting" % self.location)
        self._generate_settings()
        self._print_initialization_message()
        self._create_directories()
        self._create_general_config_file()
        self._create_default_pipeline_config_file()
        self._create_filelist()
        print

    def _generate_settings(self):
        self.command = "$ python %s\n\n" % ' '.join(sys.argv)
        self.settings = ["timestamp    =  %s\n" % time.strftime("%x %X"),
                         "language     =  %s\n" % self.language,
                         "datasource   =  %s\n" % self.datasource,
                         "source_file  =  %s\n" % self.source_file,
                         "source_path  =  %s\n" % self.source_path,
                         "target_path  =  %s\n" % self.location,
                         "shuffle      =  %s\n" % str(self.shuffle_file),
                         "git_commit   =  %s\n" % get_git_commit()]

    def _print_initialization_message(self):
        print "\n[--init] initializing %s" % self.location
        print "\n   %s" % "   ".join(self.settings)

    def _create_directories(self):
        """Create subdirectory structure in self.location."""
        print "[--init] creating directory structure in %s" % self.location
        ensure_path(self.conf_path)
        for subdir in config.DATA_DIRS:
            subdir_path = self.data_path + os.sep + subdir
            ensure_path(subdir_path)

    def _create_filelist(self):
        """Create a list of files either by copying a given list or by traversing a
        given directory."""
        print "[--init] creating %s" % self.file_list
        if self.source_file is not None:
            shutil.copyfile(self.source_file, self.file_list)
        elif self.source_path is not None:
            filenames = get_file_paths(self.source_path)
            if self.shuffle_file:
                random.shuffle(filenames)
            with open(self.file_list, 'w') as fh:
                for fname in filenames:
                    fh.write("0000\t" + fname + "\n")
        else:
            sys.exit("[--init] ERROR: " +
                     "need to define input with --filelist or " +
                     "--source-directory option, aborting")
        read_only(self.file_list)

    def _create_general_config_file(self):
        filename = os.path.join(self.conf_path, FNAME_INFO_GENERAL)
        print "[--init] creating %s" % filename
        fh = open(filename, 'w')
        fh.write(self.command)
        fh.write("".join(self.settings))
        read_only(filename)

    def _create_default_pipeline_config_file(self):
        filename = os.path.join(self.conf_path, FNAME_PIPELINE_DEFAULT)
        print "[--init] creating %s" % filename
        fh = open(filename, 'w')
        fh.write(self.pipeline_config.lstrip())
        read_only(filename)

    @staticmethod
    def populate(rconfig):
        run_populate(rconfig)

    @staticmethod
    def xml2txt(rconfig, options):
        run_xml2txt(rconfig, options)

    @staticmethod
    def txt2tag(rconfig, options,):
        run_txt2tag(rconfig, options)

    @staticmethod
    def txt2seg(rconfig, options):
        run_txt2seg(rconfig, options)

    @staticmethod
    def seg2tag(rconfig, options,):
        run_seg2tag(rconfig, options)

    @staticmethod
    def tag2chk(rconfig, options):
        run_tag2chk(rconfig, options)

    @staticmethod
    def run_default_pipeline(rconfig):
        """Runs the default pipeline, but does it without even bothering to open
        the pipeline file in the configuration."""
        run_populate(rconfig)
        run_xml2txt(rconfig, rconfig.get_options(XML2TXT))
        if rconfig.language == 'en':
            run_txt2tag(rconfig, rconfig.get_options(TXT2TAG))
        elif rconfig.language == 'cn':
            run_txt2seg(rconfig, rconfig.get_options(TXT2SEG))
            run_seg2tag(rconfig, rconfig.get_options(SEG2TAG))
        run_tag2chk(rconfig, rconfig.get_options(TAG2CHK))


def update_state(fun):
    """To be used as a decorator around functions that run one of the processing steps."""
    def wrapper(*args):
        t1 = time.time()
        files_processed, datasets = fun(*args)
        # squeeze in adding an empty line in verbose mode
        _print_empty_line(args[0].verbose)
        for dataset in datasets:
            dataset.files_processed += files_processed
            dataset.update_state(args[0].limit, t1)
    return wrapper


@update_state
def run_populate(rconfig):
    """Populate xml directory in the target directory with limit files from the
    source file list or the source directory."""

    output_name = DOCUMENT_PROCESSING_IO[POPULATE]['out']
    dataset = DataSet(POPULATE, output_name, rconfig)
    fspecs = FileSpecificationList(rconfig.filelist, dataset.files_processed, rconfig.limit)
    print "[--populate] adding %d files to %s" % (len(fspecs), dataset)
    count = 0
    for fspec in fspecs:
        count += 1
        src_file = fspec.source
        dst_file = os.path.join(rconfig.corpus, 'data', output_name,
                                dataset.version_id, 'files', fspec.target)
        # allow for compressed files, while being handed the name without extension
        if not os.path.exists(src_file):
            src_file += ".gz"
            dst_file += ".gz"
        if rconfig.verbose:
            print "[--populate] %04d %s" % (count, dst_file)
        ensure_path(os.path.dirname(dst_file))
        _copy_file(src_file, dst_file)
        compress(dst_file)
        _update_state_files_processed(dataset, count)
    return count % STEP, [dataset]


@update_state
def run_xml2txt(rconfig, options):
    """Takes the xml file and produces a txt file with a simplified document
    structure, keeping date, title, abstract, summary, description_rest,
    first_claim and other_claims. Does this by calling the document structure
    parser in onto mode if the document source is LexisNexis and uses a simple
    parser defined in xml2txt if the source is WoS."""

    input_dataset, output_dataset = _get_datasets(XML2TXT, rconfig)
    count = 0
    doc_parser = _make_parser(rconfig.language)
    workspace = os.path.join(rconfig.corpus, 'data', 'workspace')
    fspecs = FileSpecificationList(rconfig.filelist, output_dataset.files_processed, rconfig.limit)
    for fspec in fspecs:
        count += 1
        file_in, file_out = _prepare_io(XML2TXT, fspec, input_dataset, output_dataset, rconfig, count)
        uncompress(file_in)
        try:
            xml2txt.xml2txt(doc_parser, rconfig.datasource, file_in, file_out, workspace)
        except Exception:
            # just write an empty file that can be consumed downstream
            fh = codecs.open(file_out, 'w')
            fh.close()
            print "[--xml2txt] WARNING: error on", file_in
        compress(file_in, file_out)
        _update_state_files_processed(output_dataset, count)
    return count % STEP, [output_dataset]


@update_state
def run_txt2tag(rconfig, options):
    """Takes txt files and runs the tagger on them."""

    input_dataset, output_dataset = _get_datasets(TXT2TAG, rconfig)
    count = 0
    tagger = txt2tag.Tagger(rconfig.language)
    fspecs = FileSpecificationList(rconfig.filelist, output_dataset.files_processed, rconfig.limit)
    for fspec in fspecs:
        count += 1
        file_in, file_out = _prepare_io(TXT2TAG, fspec, input_dataset, output_dataset, rconfig, count)
        uncompress(file_in)
        tagger.tag(file_in, file_out)
        compress(file_in, file_out)
        _update_state_files_processed(output_dataset, count)
    return count % STEP, [output_dataset]


@update_state
def run_txt2seg(rconfig, options):
    """Takes txt files and runs the Chinese segmenter on them."""

    input_dataset, output_dataset = _get_datasets(TXT2SEG, rconfig)
    count = 0
    segmenter = cn_txt2seg.Segmenter()
    fspecs = FileSpecificationList(rconfig.filelist, output_dataset.files_processed, rconfig.limit)
    for fspec in fspecs:
        count += 1
        file_in, file_out = _prepare_io(TXT2SEG, fspec, input_dataset, output_dataset, rconfig, count)
        uncompress(file_in)
        segmenter.process(file_in, file_out)
        compress(file_in, file_out)
        _update_state_files_processed(output_dataset, count)
    return count % STEP, [output_dataset]


@update_state
def run_seg2tag(rconfig, options):
    """Takes seg files and runs the Chinese tagger on them."""

    input_dataset, output_dataset = _get_datasets(SEG2TAG, rconfig)
    count = 0
    tagger = cn_seg2tag.Tagger()
    fspecs = FileSpecificationList(rconfig.filelist, output_dataset.files_processed, rconfig.limit)
    for fspec in fspecs:
        count += 1
        file_in, file_out = _prepare_io(SEG2TAG, fspec, input_dataset, output_dataset, rconfig, count)
        uncompress(file_in)
        tagger.tag(file_in, file_out)
        compress(file_in, file_out)
        _update_state_files_processed(output_dataset, count)
    return count % STEP, [output_dataset]


@update_state
def run_tag2chk(rconfig, options):
    """Runs the np-in-context code on tagged input. Populates d3_phr_feat."""

    candidate_filter = options.get('--candidate-filter', 'off')
    chunker_rules = options.get('--chunker-rules', 'en')
    # this is a hack that maps the value of the new official name to the value
    # expected by the old name
    filter_p = True if candidate_filter == 'on' else False
    input_dataset, output_dataset = _get_datasets(TAG2CHK, rconfig)
    print "[--tag2chk] using '%s' chunker rules" % chunker_rules
    count = 0
    fspecs = FileSpecificationList(rconfig.filelist, output_dataset.files_processed, rconfig.limit)
    for fspec in fspecs:
        count += 1
        file_in, file_out = _prepare_io(TAG2CHK, fspec, input_dataset, output_dataset, rconfig, count)
        year = _get_year_from_file(file_in)
        tag2chunk.Doc(file_in, file_out, year, rconfig.language,
                      filter_p=filter_p, chunker_rules=chunker_rules, compress=True)
        _update_state_files_processed(output_dataset, count)
    return count % STEP, [output_dataset]


def _get_datasets(stage, rconfig):
    """Return two DataSet instances for the processing stage."""
    input_dataset = _find_input_dataset(stage, rconfig)
    output_dataset = _find_output_dataset(stage, rconfig)
    _print_datasets(stage, input_dataset, output_dataset)
    _check_file_counts(input_dataset, output_dataset, rconfig.limit)
    return input_dataset, output_dataset


def _find_input_dataset(stage, rconfig, data_type=None):
    """Find the input data set for a processing stage for a given configuration and return
    it. Print a warning and exit if no dataset or more than one dataset was found. If a
    data type is passed in, the dat type lookup for the stage is bypassed."""

    # Use the stage-to-data mapping to find the data_type if none was handed in
    if data_type is None:
        data_type = DOCUMENT_PROCESSING_IO[stage]['in']
    # Get all data sets D for input name
    dirname = os.path.join(rconfig.corpus, 'data', data_type)
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

    
def _find_output_dataset(stage, rconfig, data_type=None):
    """Find the output data set of a stage for a given configuration and return
    it. Print a warning and exit if no dataset or more than one dataset was
    found."""

    # Use the stage-to-data mapping to find the output names
    if data_type is None:
        data_type = DOCUMENT_PROCESSING_IO[stage]['out']
    # Get all data sets D for input name
    dirname = os.path.join(rconfig.corpus, 'data', data_type)
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
            dataset.load_config_and_state()
        print "[%s] created %s" % (stage, dataset)
        return dataset


def _print_empty_line(verbose):
    if verbose:
        print


def _print_datasets(stage, input_dataset, output_dataset):
    print "[%s] input %s" % (stage, input_dataset)
    print "[%s] output %s" % (stage, output_dataset)


def _print_file_progress(stage, filename, count, rconfig):
    if rconfig.verbose:
        print "[%s] %04d %s %s" \
              % (stage, count, os.path.basename(rconfig.corpus), filename)


def _check_file_counts(input_dataset, output_dataset, limit):
    if input_dataset.files_processed < output_dataset.files_processed + limit:
        print "[check_file_counts] " + \
              "WARNING: input dataset does not have enough processed files"
        sys.exit("Exiting...")


def _prepare_io(stage, fspec, input_dataset, output_dataset, rconfig, count):
    """Generate the file paths for the datasets and make sure the path to the file exists for
    the output dataset."""
    filename = fspec.target
    _print_file_progress(stage, filename, count, rconfig)
    file_id = filename[1:] if filename.startswith(os.sep) else filename
    file_in = os.path.join(input_dataset.path, 'files', file_id)
    file_out = os.path.join(output_dataset.path, 'files', file_id)
    ensure_path(os.path.dirname(file_out))
    return file_in, file_out


def _make_parser(language):
    """Return a document structure parser for language."""
    parser = Parser()
    parser.onto_mode = True
    mappings = {'en': 'ENGLISH', 'de': "GERMAN", 'cn': "CHINESE"}
    parser.language = mappings[language]
    return parser


def _update_state_files_processed(dataset, count):
    # TODO: does this mean that you miss some if total_count % STEP != 0
    if count % STEP == 0:
        dataset.update_processed_count(STEP)


def _get_year_from_file(file_name):
    """The only reliable way to get the year is to open the file and read the data
    from it. In the past we would try to finagle the year from the directory path,
    but that was way too brittle."""
    with open_input_file(file_name) as fh:
        year = None
        read_year = False
        for line in fh:
            if line.startswith('FH_TITLE:'):
                pass
            elif line.startswith('FH_DATE:'):
                read_year = True
            elif line.startswith('FH_'):
                return "9999" if year is None else year
            elif read_year:
                # skip empty lines (shouldn't be there though)
                if not line.strip():
                    continue
                year = line.strip()[:4]
                return year
    # make sure we never return None
    return '9999'


def _copy_file(src_file, dst_file):
    """Copy a source file into its destination in the corpus. In some cases the
    source file may not exist."""
    try:
        shutil.copyfile(src_file, dst_file)
    except IOError:
        print "%sWARNING: source file does not exist, not copying" % ' ' * 18
        print "%s%s" % src_file % ' ' * 18


class FileSpecificationList(object):

    """Maintains a list of FileSpecifications for a corpus, initialized from the
    list of files in the configuration of the Corpus. This picks out a subset of
    the files listed by using the index of the first file requested and a total
    number. The default file list is in config/files.txt."""

    def __init__(self, filename, start=0, limit=500):
        """Populate a list with n=limit file specifications from the filelist in
        filename, starting from line n=start. This function will return less than
        n=limit files if their were less than n=limit lines left in filename, it
        will return an empty list if start is larger than the number of lines in
        the file."""
        self.data = []
        current_count = start
        fh = open(filename)
        line_number = 0
        while line_number < current_count:
            fh.readline(),
            line_number += 1
        lines_read = 0
        while lines_read < limit:
            line = fh.readline().strip()
            if line == '':
                break
            self.data.append(FileSpecification(line))
            lines_read += 1
        fh.close()

    def __len__(self):
        return len(self.data)

    def __getitem__(self, item):
        return self.data[item]


class FileSpecification(object):

    """A FileSpecification is created from a line from a file that specifies the
    sources. Such a file has two mandatory columns: year and source_file. These
    fill the year and source instance variables in the FileSpec. The target
    instance variable is by default the same as the source, but can be overruled
    if there is a third column in the file. Example input lines:

       1980    /data/patents/xml/us/1980/12.xml   1980/12.xml
       1980    /data/patents/xml/us/1980/13.xml   1980/13.xml
       1980    /data/patents/xml/us/1980/14.xml
       0000    /data/patents/xml/us/1980/15.xml

    FileSpec can also be created from a line with just one field, in that case
    the year and source are set to None and the target to the only field. This
    is typically used for files that simply list filenames for testing or
    training.
    """

    def __init__(self, line):
        fields = line.strip().split("\t")
        if len(fields) > 1:
            self.year = fields[0]
            self.source = fields[1]
            self.target = fields[2] if len(fields) > 2 else fields[1]
        else:
            self.year = None
            self.source = None
            self.target = fields[0]
        self._strip_slashes()

    def __str__(self):
        return "<%s %s %s>" % (self.year, self.source, self.target)

    def _strip_slashes(self):
        if self.target.startswith(os.sep):
            self.target = self.target[1:]
