"""

Adding new files from the update:

    ln-us-updates-2014-09-23-scrambled.txt
    ln-us-updates-2014-09-23-scrambled-basename.txt
    ln-us-updates-2014-09-23-scrambled-patnum.txt
    
The first is a file list created on eldrad. The seond is the same list but just
the basename (using cut -f11 -d'/').

"""


import os, sys, re, time, shutil
import config
from corpus import Corpus
sys.path.append(os.path.abspath('../..'))
from ontology.utils.file import compress, ensure_path


re_PATENT_NUMBER = re.compile('^(B|D|H|HD|RE|PP|T)?(\d+)(.*)')

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


def get_patent_id(basename):
    id = os.path.splitext(basename)[0]
    if id.startswith('US'):
        id = id[2:]
    result = re_PATENT_NUMBER.match(id)
    if result is None:
        print "WARNING: no match on", fname
        return None
    prefix = result.groups()[0]
    kind_code = result.groups()[-1]
    number = ''.join([g for g in result.groups()[:-1] if g is not None])
    return (prefix, kind_code, number)


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

    
def analyze_not_in_repo():
    for line in open('not-in-repo.txt'):
        pass



class Repository(object):
    
    DIR = '/home/j/corpuswork/fuse/FUSEData/repositories'

    def __init__(self, dirname):
        """Initialize by storing the physical location of the repository. The
        argument is a relative or absolute path to a repository. It could also
        be a sub directory of the standard location of all repositories. If the
        repository does not yet exist, initialize it on disk, in that case, the
        argument is considered to be an absolute path or a path relative to the
        location of this script."""
        if os.path.isdir(dirname):
            self.dir = dirname
            print self
        elif os.path.isdir(os.path.join(Repository.DIR, dirname)):
            self.dir = os.path.join(Repository.DIR, dirname)
            print self
        else:
            self._initialize(dirname)
            print self

    def __str__(self):
        return "<Repository '%s'>" % self.dir

    def _initialize(self, dirname):
        print "Initializing on disk"
        self.dir = dirname
        os.makedirs(dirname)
        os.makedirs(self.idx_dir())
        os.makedirs(self.doc_dir())
        os.makedirs(self.data_dir())
        os.makedirs(self.proc_dir())
        open(self.identifier_file(), 'w')
        open(self.filelist_file(), 'w')

    def read_identifiers(self):
        """Return a dictionary with as keys all the identifiers in the
        repository. This works for now with smaller repositories, but we may
        need to start using an sqlite database."""
        identifiers = {}
        fh = open(self.identifier_file())
        for line in fh:
            identifiers[line.strip()] = True
        return identifiers
    
    def idx_dir(self): return os.path.join(self.dir, 'index')
    def doc_dir(self): return os.path.join(self.dir, 'documents')
    def data_dir(self): return os.path.join(self.dir, 'data','sources')
    def proc_dir(self): return os.path.join(self.dir, 'data', 'processed')

    def identifier_file(self): return os.path.join(self.idx_dir(), 'identifiers.txt')
    def filelist_file(self): return os.path.join(self.idx_dir(), 'files.txt')


class PatentRepository(Repository):

    def add_corpus(self, corpus_path, language='en', datasource='ln',
                   limit=sys.maxint):

        """Adds corpus data to the repository, both the source data (taken from
        the external source of the corpus) and the processed files. Updates the
        list of identifiers and the list of files in the index by appending
        elements to the end o fthose files. Only adds patents that are not in
        the identifier list.

        The input corpus is expected to be one of the corpora created by
        step1_init.py and step2_process.py.

        Unlike with creating corpora, where we can create and process various
        corpora on different cores/machines, this method should never be run in
        parallel, always import one corpus at a time and wait for it to
        finish."""

        corpus = Corpus(language, datasource, None, None, corpus_path, 
                        config.DEFAULT_PIPELINE, False)

        self.current_identifiers = self.read_identifiers()
        self.fh_identifiers = open(self.identifier_file(), 'a')
        self.fh_files = open(self.filelist_file(), 'a')
        self.fh_processed = {}
        for step in PROCESSING_STEPS:
            self.fh_processed[step] = open("%s%sprocessed-%s.txt" %
                                           (self.idx_dir(), os.sep, step), 'a')

        c = 0
        for line in open(corpus.file_list):
            c += 1
            if c > limit: break
            fields = line.rstrip("\n\r\f").split("\t")
            # these are the external source and the corpus-local source
            source = fields[1]
            local_source = fields[2] if len(fields)> 2 else source
            source = validate_filename(source)
            if source is None:
                print "WARNING, source not available for %s" % source
                continue
            (id, path, basename) = parse_patent_path(source)
            if id in self.current_identifiers:
                print "Skipping", source
            else:
                t = time.localtime()
                self._add_patent_source(t, source, id, path, basename)
                self._add_patent_processed(t, corpus, local_source, id, path, basename)

    def _add_patent_source(self, t, source, id, path, basename):
        path = os.sep.join(path)
        print "Adding", source, 'to', path
        target_dir = os.path.join(self.data_dir(), path)
        target_file = os.path.join(target_dir, basename)
        ensure_path(target_dir)
        shutil.copyfile(source, target_file)
        compress(target_file)
        size = get_file_size(target_file)
        self.fh_identifiers.write("%s\n" % id)
        self.add_entry_to_file_index(t, id, size, path, basename)

    def _add_patent_processed(self, t, corpus, local_source, id, path, basename):
        for step in PROCESSING_STEPS:
            fname = os.path.join(corpus.location,
                                'data', step, '01', 'files', local_source)
            fname = validate_filename(fname)
            if fname is not None:
                print '  ', fname
                target_dir = os.path.join(self.proc_dir(), step, os.sep.join(path))
                target_file = os.path.join(target_dir, basename)
                print '  ', target_file
                ensure_path(target_dir)
                shutil.copyfile(fname, target_file)
                compress(target_file)
                self.add_entry_to_processed_index(t, id, step)

    def add_entry_to_file_index(self, t, id, size, path, basename):
        timestring = time.strftime("%Y%m%d:%H%M%S", t)
        if basename.endswith('.gz'):
            basename = basename[:-3]
        self.fh_files.write("%s\t%s\t%d\t%s%s%s\n" %
                            (timestring, id, size, path, os.sep, basename))

    def add_entry_to_processed_index(self, t, id, step):
        # for this, maybe use processed-d1_txt.txt with identifiers as context?
        # NOOOO!, must add at least the git repo
        timestring = time.strftime("%Y%m%d:%H%M%S", t)
        self.fh_processed[step].write("%s\t%s\n" % (timestring, id))


def validate_filename(fname):
    """Validate the filename by checking whether it exists, potentially in
    gzipped form. Return the actual filename None if there was no file. Note
    that fname ty[ically never includes the .gz extension"""
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

def patentid2path(id):
    """Split the patent identifier into three parts of a path. The first part of
    the path is either a year, one or two letters (D, PP, T etcetera), The last
    part is the last two digits of the identifier, which ensures that the
    deepest directories in the tree never have more that 100 patents. The middle
    part is what remains of the indentifier."""
    if id[:2] in ('19', '20'):
        return id[:4], id[4:-2], id[-2:]
    elif id[0].isalpha() and id[1].isalpha():
        return  id[:2], id[2:-2], id[-2:]
    elif id[0].isalpha():
        return  id[:1], id[1:-2], id[-2:]
    else:
        return  id[:2], id[2:-2], id[-2:]

    

if __name__ == '__main__':

    dirname = sys.argv[1]
    repo = PatentRepository(dirname)
    corpus_path = '/home/j/corpuswork/fuse/FUSEData/corpora/ln-us-sample-500'
    corpus_path ='data/patents/corpora/sample-us'
    repo.add_corpus(corpus_path, 10)
