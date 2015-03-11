"""repository.py

Code to build, manage and access repositories.

A repository needs to be initialized once. Once you have a repository you can do
several things:

    1- adding all files from a corpus (both sources and processed files)
    2- adding sources from a list of files
    3- querying the repository for data
    4- analyzing the repository

These are in varying stages of completion (and non-completion). See below for
more details.


USAGE:

    $ python repository OPTIONS

    OPTIONS:
        --initialize
        --add-corpus
        --analyze
        (-c | --corpus) PATH
        (-r | --repository) PATH


INITIALIZATION

To initialize a repository:

    $ python repository.py --initialize --repository test

After a repository is initialized it has the following structure:

    documents/
    logs/
    index/
       idx-dates.txt
       idx-identifiers.txt
       idx-files.txt
       idx-processed-d1_txt.txt
       idx-processed-d2_seg.txt
       idx-processed-d2_tag.txt
       idx-processed-d3_phr_feats.txt
    data/
       sources/
       processed/

All directories are empty, except for index/, which has a couple of index files
that are all empty (because the repository is still empty). Other directories
may be added to repositories, for example a directory with scripts for local
repository-spefici processing or a directory with lists of files. Other index
files may be added over time, some specific to particular repository types.

TODO: add an SQLite database that replaces all the index files. The index files
could still be kept around as a kind of journal files.

There will be several kinds of repositories, each making different assumptions
on identifiers:

    PatentRepository
    CnkiRepository
    PubmedRepository

A PatentRepository assumes that the basename of a file is a unique file and
stores patents using that uniqueness. It is the only repository type that exists
at this point. When more types come into being a new option will be added.

The index files contain a list of records with the following fields (this is for
patents):

    idx-ids.txt:
        numerical identifier
    idx-files.txt:
        timestamp
        numerical identifier
        size of source file (compressed)
        path i nrepository
    idx-dates:
        not yet used
    idx-processed-X.txt:
        timestamp
        git commit
        numerical id
        options (zero or more columns)


ADDING CORPUS DATA

To add all data from a corpus:

    $ python repository.py --add-corpus -r test -c data/patents/corpora/sample-us

Existing data will not be overwritten. At some point we may add a flag that
allows you to overwrite existing data. 


More corpora can be added later. This needs to be done one corpus at a time, no
conccurrency is implemented.

During a corpus load, source files are added to /data/sources and processed
files to data/processed. For patents, the directory strcuture in data/sources is
generated from the filename, for the sample corpus we end up with the following
files in a three-level directory structure:

    data/sources/42/365/96/US4236596A.xml.gz
    data/sources/42/467/08/US4246708A.xml.gz
    data/sources/42/543/95/US4254395A.xml.gz
    data/sources/41/927/70/US4192770A.xml.gz

This structure is mirrored under data/processed, with the addition of the name
of the processing step (d1_txt, d2_seg, d2_tag or d3_phr_feats), for example,
for the tagged files we get:

    data/processed/d2_tag/42/365/96/US4236596A.xml.gz
    data/processed/d2_tag/42/467/08/US4246708A.xml.gz
    data/processed/d2_tag/42/543/95/US4254395A.xml.gz
    data/processed/d2_tag/41/927/70/US4192770A.xml.gz

Corpus loads also update the index files and add a time-stamped log file to the
logs directory.



NOTES (THESE SHOULD BE ADDED TO ln-us)

Adding new files from the update:

    ln-us-updates-2014-09-23-scrambled.txt
    ln-us-updates-2014-09-23-scrambled-basename.txt
    ln-us-updates-2014-09-23-scrambled-patnum.txt

The first is a file list created on eldrad. The seond is the same list but just
the basename (using cut -f11 -d'/').

"""


import os, sys, re, time, shutil, getopt
from config import DEFAULT_PIPELINE
from corpus import Corpus
sys.path.append(os.path.abspath('../..'))
from ontology.utils.file import compress, ensure_path, read_only, make_writable


REPOSITORY_DIR = '/home/j/corpuswork/fuse/FUSEData/repositories'

re_PATENT = re.compile('^(B|D|H|HD|RE|PP|T)?(\d+)(.*)')


LISTS_DIR = '/home/j/corpuswork/fuse/FUSEData/lists'
IDX_FILE = LISTS_DIR + '/ln_uspto.all.index.txt'
UPDATES_FILE = LISTS_DIR + '/ln-us-updates-2014-09-23-scrambled-basename.txt'

PROCESSING_STEPS = ('d1_txt', 'd2_seg', 'd2_tag', 'd3_phr_feats')


def analyze_filenames(fname):    
    """Checks whether all the numbers we extract from the filenames are
    unique. This is the case for IDX_FILE."""
    number2name = {}
    number2path = {}
    fh = open(fname)
    basedir = fh.readline()
    c = 1
    for line in fh:
        c += 1
        if c % 100000 == 0: print c
        #if c > 100000: break
        (number, adate, pdate, path) = line.rstrip("\n\f\r").split("\t")
        name = os.path.splitext(os.path.basename(path))[0]
        if number2name.has_key(number):
            print "Warning, duplicate number", number, path
        number2name.setdefault(number,[]).append(name)
        number2path.setdefault(number,[]).append(path)


def analyze_filename_lengths(fname):    
    """Checks lengths of file names."""
    lengths = {}
    fh = open(fname)
    basedir = fh.readline()
    c = 1
    fhs = { 5: open('lengths-05.txt', 'w'),
            6: open('lengths-06.txt', 'w'),
            7: open('lengths-07.txt', 'w'),
            8: open('lengths-08.txt', 'w'),
            11: open('lengths-11.txt', 'w'),
            12: open('lengths-12.txt', 'w') }
    for line in fh:
        c += 1
        if c % 100000 == 0: print c
        #if c > 100000: break
        (number, adate, pdate, path) = line.rstrip("\n\f\r").split("\t")
        name = os.path.splitext(os.path.basename(path))[0]
        number_length = len(number)
        lengths[number_length] = lengths.get(number_length,0) + 1
        fhs[number_length].write("%s\n" % name)
    print lengths


def test_directory_structure():
    """Some experiments to see how to do the directory structure of the
    repository. The goal is to have the filenumber reflected in the path in a
    predicatble manner. It looks like having a three-deep structure works
    nicely. The deepest level just encodes the last two numbers of the number
    (so no more than 100 documents in the leaf directories). Then the first is
    either a year, one or two letters, or two numbers. The middle directory is
    whatever remains of the filename."""
    fh = open('tmp-patnums.txt')
    fh.readline()
    dirs = {}
    c = 0
    for line in fh:
        c += 1
        if c % 100000 == 0: print c
        num = line.strip()
        (dir1, dir2, dir3) = patentid2path(num)
        dirs.setdefault(dir1,{})
        dirs[dir1][dir2] = dirs[dir1].get(dir2,0) + 1
        if not dir1 and dir2 and dir3:
            print num, dir1, dir2, dir3
    for dir1 in sorted(dirs):
        print '>', dir1, len(dirs[dir1])
        for dir2 in sorted(dirs[dir1]):
            print '  ', dir2, dirs[dir1][dir2]


def compare_lists(list1, list2):

    """list1 is an index with four columns, list2 just has the one column."""

    in1 = open(list1)
    in2 = open(list2)
    out1 = open("out-in-repo.txt", 'w')
    out2 = open("out-not-in-repo.txt", 'w')
    basedir = in1.readline()
    repo = {}
    c = 1
    for line in in1:
        c += 1
        if c % 100000 == 0: print c
        repo[line.split("\t")[0]] = True
    in_repo = 0
    not_in_repo = 0
    c = 0
    for line in in2:
        c += 1
        if c % 100000 == 0: print c
        basename = line.strip()
        (prefix, code, id) = get_patent_id(basename)
        if id in repo:
            in_repo += 1
            out1.write("%s\n" % basename)
        else:
            not_in_repo += 1
            out2.write("%s\n" % basename)
    print 'in_repo', in_repo
    print 'not_in_repo', not_in_repo



class Repository(object):

    def __init__(self, dirname):
        """Initialize by storing the physical location of the repository. The
        argument is a relative or absolute path to a repository. Often, this is
        a directory insize of REPOSITORY_DIR, which is the standard location of
        all repositories. If the repository does not yet exist it is initialized
        on disk."""
        self.dir = dirname
        self.idx_dir = os.path.join(self.dir, 'index')
        self.doc_dir = os.path.join(self.dir, 'documents')
        self.log_dir = os.path.join(self.dir, 'logs')
        self.data_dir = os.path.join(self.dir, 'data','sources')
        self.proc_dir = os.path.join(self.dir, 'data', 'processed')
        self.idx_ids = os.path.join(self.idx_dir, 'idx-ids.txt')
        self.idx_files = os.path.join(self.idx_dir, 'idx-files.txt')
        self.idx_dates = os.path.join(self.idx_dir, 'idx-dates.txt')
        self._initialize_directory()

    def __str__(self):
        return "<Repository '%s'>" % self.dir

    def _initialize_directory(self):
        """Initialize directory structure and files on disk if needed."""
        if not os.path.isdir(self.dir):
            for d in (self.doc_dir, self.log_dir, self.idx_dir,
                      self.data_dir, self.proc_dir):
                os.makedirs(d)
            for fname in self._index_files():
                open(fname, 'w').close()
                read_only(fname)

    def _index_files(self):
        """Return a list of all index files."""
        fnames = [self.idx_ids, self.idx_files, self.idx_dates]
        for step in PROCESSING_STEPS:
            fnames.append("%s%sidx-processed-%s.txt" % (self.idx_dir, os.sep, step))
        return fnames

    def read_identifiers(self):
        """Return a dictionary with as keys all the identifiers in the
        repository. This works for now with smaller repositories, but we may
        need to start using an sqlite database."""
        identifiers = {}
        fh = open(self.idx_ids)
        for line in fh:
            identifiers[line.strip()] = True
        return identifiers
    
    def analyze(self):
        files = 0
        size = 0
        for line in open(self.idx_files):
            (timestamp, id, filesize, path) = line.rstrip().split("\t")
            files += 1
            size += int(filesize)
        print self
        print "  %6sMB  - source size (compressed)" % (size/1000000)
        print "  %8s -  number of files" % files


class PatentRepository(Repository):

    def add_corpus(self, corpus_path, language='en', datasource='ln',
                   limit=sys.maxint):

        """Adds corpus data to the repository, both the source data taken from
        the external source of the corpus and the processed files. Updates the
        list of identifiers, the list of files and the list of processed files
        in the index by appending elements to the end of those files. Only adds
        patents that are not in the identifier list.

        The input corpus is expected to be one of the corpora created by
        step1_init.py and step2_process.py.

        Unlike with creating corpora, where we can create and process various
        corpora on different cores/machines, this method should never be run in
        parallel, always import one corpus at a time and wait for it to
        finish."""

        current_identifiers = self.read_identifiers()
        corpus = CorpusInterface(language, datasource, corpus_path)
        self._open_index_files()
        logfile = os.path.join(self.log_dir, "add-corpus-%s.txt" % timestamp())
        self.log = open(logfile, 'w')
        log("Adding corpus %s" % corpus_path, self.log, notify=True)
        c = 0
        t1 = time.time()
        added = 0
        try:
            for line in open(corpus.file_list):
                c += 1
                if c % 100 == 0: print c
                if c > limit: c -= 1; break
                added_p = self._add_patent(current_identifiers, corpus, c, line)
                if added_p:
                    added += 1
        except:
            log("An Exception occurred - exiting...", self.log, notify=True)
        finally:
            log("Added %d out of %d in %d seconds" % (added, c, time.time() - t1),
                self.log, notify=True)
            self._close_log()
            self._close_index_files()


    def _open_index_files(self):
        for fname in self._index_files():
            make_writable(fname)
        self.fh_ids = open(self.idx_ids, 'a')
        self.fh_files = open(self.idx_files, 'a')
        self.fh_dates = open(self.idx_dates, 'a')
        self.fh_processed = {}
        for step in PROCESSING_STEPS:
            fname = "%s%sidx-processed-%s.txt" % (self.idx_dir, os.sep, step)
            self.fh_processed[step] = open(fname, 'a')

    def _close_log(self):
        logname = self.log.name
        self.log.close()
        read_only(logname)

    def _close_index_files(self):
        fhs = [self.fh_ids, self.fh_files, self.fh_dates] + self.fh_processed.values()
        for fh in fhs:
            fname = fh.name
            fh.close()
            read_only(fname)

    def _add_patent(self, current_identifiers, corpus, c, line):
        """Add a document source and the processed files. Do nothing if source
        cannot be found or if source is already in the list of current
        identifiers. Return True is data were added, false otherwise."""
        # TODO: there is a nasty potential problem here. Suppose we are
        # processing a file in a corpus and that file was in another corpus that
        # we imported before. And suppose that in the erarlier corpus this file
        # was not processed and it was processed in the later corpus. In that
        # case the processed files are not copied. Even if this occurs, it will
        # not impact the integrity of the repository.
        (external_source, local_source) = get_filelist_paths(line)
        external_source = validate_filename(external_source)
        if external_source is None:
            log("%05d WARNING, source not available for %s" % (c, external_source),
                self.log, notify=True)
            return False
        (id, path, basename) = parse_patent_path(external_source)
        if id in current_identifiers:
            log("%05d Skipping %s" % (c, external_source), self.log)
            return False
        else:
            t = timestamp()
            log("%05d Adding %s to %s" % (c, external_source, os.sep.join(path)),
                self.log)
            self._add_patent_source(t, external_source, id, path, basename)
            self._add_patent_processed(t, corpus, local_source, id, path, basename)
            return True

    def _add_patent_source(self, t, source, id, path, basename):
        path = os.sep.join(path)
        target_dir = os.path.join(self.data_dir, path)
        target_file = os.path.join(target_dir, basename)
        copy_and_compress(source, target_dir, target_file)
        size = get_file_size(target_file)
        self.fh_ids.write("%s\n" % id)
        self.add_entry_to_file_index(t, id, size, path, basename)

    def _add_patent_processed(self, t, corpus, local_source, id, path, basename):
        for step in PROCESSING_STEPS:
            fname = get_path_of_processed_file(corpus, step, local_source)
            if fname is not None:
                target_dir = os.path.join(self.proc_dir, step, os.sep.join(path))
                target_file = os.path.join(target_dir, basename)
                log("      Adding %s" % target_file, self.log)
                copy_and_compress(fname, target_dir, target_file)
                #self.add_entry_to_processed_index(t, id, step, corpus.git_commits)
                self.add_entry_to_processed_index(t, id, step, corpus)

    def add_entry_to_file_index(self, t, id, size, path, basename):
        if basename.endswith('.gz'):
            basename = basename[:-3]
        self.fh_files.write("%s\t%s\t%d\t%s%s%s\n" %
                            (t, id, size, path, os.sep, basename))

    def add_entry_to_processed_index(self, t, id, step, corpus):
        commit = corpus.git_commits.get(step)
        options = "\t".join(corpus.options[step])
        if options: options = "\t" + options
        self.fh_processed[step].write("%s\t%s\t%s%s\n" % (t, commit, id, options))


class CorpusInterface(object):

    """Object that acts as an intermediary to a corpus. It emulates part of the
    interface of corpus.Corpus (location and file_list instance variables and
    adds information on commits in self.git_commits and processing step options
    in self.options."""

    def __init__(self, language, datasource, corpus_path):
        self.corpus = Corpus(language, datasource, None, None, corpus_path,
                             DEFAULT_PIPELINE, False)
        self.location = self.corpus.location
        self.file_list = self.corpus.file_list
        self._collect_git_commits()
        self._collect_step_options()

    def _collect_git_commits(self):
        """Collect the git commits for all steps in the processing chain."""
        self.git_commits = {}
        for step in PROCESSING_STEPS:
            commit = self._find_git_commit_from_processing_history(step)
            self.git_commits[step] = commit

    def _find_git_commit_from_processing_history(self, step):
        """Returns the git commit for the code that processed this step of the
        corpus. Returns the earliest commit as found in the corpus."""
        fname = os.path.join(self.location, 'data', step, '01', 'state',
                             'processing-history.txt')
        if os.path.exists(fname):
            line = open(fname).readline()
            return line.rstrip("\n\r\f").split("\t")[3]
        return None

    def _collect_step_options(self):
        self.options = {}
        for step in PROCESSING_STEPS:
            fname = os.path.join(self.location, 'data', step, '01', 'config', 'pipeline-head.txt')
            if not os.path.exists(fname):
                options = []
            else:
                content = open(fname).readline().split()
                options = content[1:]
            self.options[step] = options



def timestamp():
    return time.strftime("%Y%m%d:%H%M%S")

def get_filelist_paths(line):
    """ a file list has two or three columns, the second is the full path to the
    source and the third, if it exists, is the local path.By default the local
    path is a full copy of the source path. Return the source path and resolved
    local path."""
    fields = line.rstrip("\n\r\f").split("\t")
    source = fields[1]
    local_source = fields[2] if len(fields)> 2 else source
    return (source, local_source)

def get_path_of_processed_file(corpus, step, local_source):
    """Build a full file path given a corpus, a processing step and a local
    source file"""
    fname = os.path.join(corpus.location,
                         'data', step, '01', 'files', local_source)
    return validate_filename(fname)

def validate_filename(fname):
    """Validate the filename by checking whether it exists, potentially in
    gzipped form. Return the actual filename or return None if there was no
    file. Note that fname typically never includes the .gz extension"""
    if os.path.exists(fname + '.gz'): return fname + '.gz'
    elif os.path.exists(fname): return fname
    else: return None

def get_file_size(fname):
    """Returns the size of fname if it exists, or else the size of fname.gz."""
    if not os.path.exists(fname):
        fname += '.gz'
    return os.path.getsize(fname)

def parse_patent_path(path):
    """take a source path (of which only the basename is relevant) and get the
    identifier, prefix, kind (a1, A2..) and the path as used in the
    repository."""
    basename = os.path.basename(path)
    basename_bare = os.path.splitext(basename)[0]
    prefix, kind, id = get_patent_id(basename_bare)
    path = patentid2path(id)
    return id, path, basename

def get_patent_id(basename):
    """Get the prefix, kind code and unique numerical identifier from the file
    name. Prefix and kind code can both be empty strings."""
    id = os.path.splitext(basename)[0]
    if id.startswith('US'):
        id = id[2:]
    result = re_PATENT.match(id)
    if result is None:
        print "WARNING: no match on", fname
        return None
    prefix = result.groups()[0]
    kind_code = result.groups()[-1]
    number = ''.join([g for g in result.groups()[:-1] if g is not None])
    return (prefix, kind_code, number)

def patentid2path(id):
    """Generate a pathname from the patent identifier. Split the patent
    identifier into three parts of a path. The first part of the path is either
    a year, one or two letters (D, PP, T etcetera), The last part is the last
    two digits of the identifier, which ensures that the deepest directories in
    the tree never have more that 100 patents. The middle part is what remains
    of the indentifier. Only the first and middle parts are returned"""
    if id[:2] in ('19', '20'):
        return id[:4], id[4:-2]
    elif id[0].isalpha() and id[1].isalpha():
        return  id[:2], id[2:-2]
    elif id[0].isalpha():
        return  id[:1], id[1:-2]
    else:
        return  id[:2], id[2:-2]

def copy_and_compress(source, target_dir, target_file):
    """Copy source to target file, making sure there is a directory. Compress
    the new file."""
    ensure_path(target_dir)
    shutil.copyfile(source, target_file)
    compress(target_file)

def log(text, fh, notify=False):
    fh.write("%s\n" % text)
    if notify:
        print text

def check_repository_existence(repository):
    if not os.path.exists(repository):
        exit("WARNING: repository '%s' does not exist" % repository)

def validate_location(path):
    if os.path.isdir(path):
        return path
    if os.path.isdir(os.path.join(REPOSITORY_DIR, path)):
        return os.path.join(REPOSITORY_DIR, path)
    exit("WARNING: repository '%s' does not exist" % path)



if __name__ == '__main__':

    options = ['initialize', 'add-corpus', 'analyze', 'repository=', 'corpus=']
    (opts, args) = getopt.getopt(sys.argv[1:], 'r:c:', options)

    init_p = False
    add_corpus_p = False
    analyze_p = False
    repository = None
    corpus = None

    for opt, val in opts:
        if opt == '--initialize': init_p = True
        if opt == '--add-corpus': add_corpus_p = True
        if opt == '--analyze': analyze_p = True
        if opt in ('-r', '--repository'): repository = val
        if opt in ('-c', '--corpus'): corpus = val

    if repository is None:
        exit("WARNING: missing repository argument")
    elif init_p:
        if os.path.exists(repository):
            exit("WARNING: repository '%s' already exists" % repository)
        print "Initializing repository '%s'" % repository
        PatentRepository(repository)
    else:
        repository = validate_location(repository)
        if add_corpus_p:
            if corpus is None:
                exit("WARNING: missing corpus argument")
            PatentRepository(repository).add_corpus(corpus)
        elif analyze_p:
            PatentRepository(repository).analyze()
