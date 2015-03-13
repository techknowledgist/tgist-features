"""view.py

An interface to views.

Views are defined by two things: a list of identifiers for documents and a
repository. They have no content of their own, except for some bookkeeping on
the repository and optionally on the corpus they were created from.


USAGE (COMMAD LINE):

    $ python view.py --initialize-from-corpus --view PATH --repository PATH --corpus PATH
    $ python view.py --analyze --view PATH

The first form creates a view from a corpus. The view is linked to a repository,
which must be an existing repository (it can be in repository.REPOSITORY_DIR or
else where). After initialization, the directory structure of a view is as follows:

    corpus-config/
    corpus-data/
    index/
       files.txt
    repository.txt

The file repository.txt holds a string that points to the repository. The file
index/files.txt contains a list of identifier-path pairs. The path is the local
path in the repository. This path is calculated from the identifier. This is
specific for patents and may change in the future when views to non-patent
repositories are created, probably by making the path field optional. The
corpus-config and corpus-data directories contain some information lifted from
the corpus. After initialization they are not essential to th eworkings of a
view and are mostly a historical record.

Example:

    python view.py \
           --initialize-from-corpus \
           --view test-view \
           --repository ln-us \
           --corpus /home/j/corpuswork/fuse/FUSEData/corpora/ln-us-A21-computers/subcorpora/1997

The second form checks whether identifiers listed in index/files.txt actually
can be associated with files in the repository. It writes results to an info
directory, which will be created the first time --analyze is executed.


USAGE (IN SCRIPS):

For use in other scripts, five iterator generating methods are provided in the
View class: sources(), d1_txt(), d2_seg(), d2_tag() and d3_phr_feats(). The
iterators will return a list of elements, where each element is either a
absolute path that points to an existing file in th erepository or None, for
those cases where an identifier was not associated with a repository file.

As an example, consider the common case of a scripts that needs access to all
tagged files in a view. This can be done as follows:

    import view
    a21_view = view.View('view-A21-computers-1997')
    tagged_files = a21_view.d2_tag()
    for fname in tagged_files:
        if fname is not None:
            print fname

This will print a list of absolute paths accessable through the view.

"""

import os, sys, shutil, glob, getopt, time
import repository


def create_view(view_dir, repository_dir):
    """Create a new empty view in directory view_dir and hook it up to the
    repository in repository_dir."""
    if os.path.exists(view_dir):
        exit("Directory '%s' already exists." % view_dir)
    if not repository_exists(repository_dir):
        exit("Repository '%s' does not exist" % repository_dir)
    os.makedirs(view_dir)
    with open(os.path.join(view_dir, 'repository.txt'), 'w') as fh:
        fh.write("%s\n" % repository_dir)
    view = View(view_dir)
    os.makedirs(view.index_dir)

def create_view_from_corpus(corpus_dir, view_dir, repository_dir):
    """Create a new view on a repository and set up its index so it views the
    part of the repository that was included in the corpus."""
    if not os.path.exists(corpus_dir):
        exit("WARNING: corpus directory does not exist")
    create_view(view_dir, repository_dir)
    view = View(view_dir)
    view.add_corpus_data(corpus_dir)
    view.create_index_from_corpus_data()

def repository_exists(dirname):
    """Simply checks whether dirname exists, also looks in the default
    repository directory."""
    return os.path.isdir(dirname) \
           or os.path.isdir(os.path.join(repository.REPOSITORY_DIR, dirname))


class View(object):

    def __init__(self, path):
        self.dir = path
        self.repository_file =  os.path.join(self.dir, 'repository.txt')
        self.corpus_config_dir = os.path.join(self.dir, 'corpus-config')
        self.corpus_data_dir = os.path.join(self.dir, 'corpus-data')
        self.index_dir = os.path.join(self.dir, 'index')
        self.filelist_file = os.path.join(self.index_dir, 'files.txt')
        with open(self.repository_file) as fh:
            self.repository = repository.Repository(fh.read().strip())

    def __str__(self):
        return "<View '%s' on '%s>" % (self.dir, self.repository.dir)

    def is_created_from_corpus(self):
        return os.path.exists(self.corpus_config_dir)

    def add_corpus_data(self, corpus_dir):
        """Add some of the contents of a corpus to the view. This includes
        everything in the config directory as well as the state and config files
        for each step in the data directory. For the latter, the directory is
        flattened and the files contain the step and config part of the
        path. Does NOT include the files."""
        os.makedirs(self.corpus_config_dir)
        os.makedirs(self.corpus_data_dir)
        corpus_config_dir = os.path.join(corpus_dir, 'config')
        corpus_data_dir = os.path.join(corpus_dir, 'data')
        for fname in os.listdir(corpus_config_dir):
            shutil.copyfile(os.path.join(corpus_config_dir, fname),
                            os.path.join(self.corpus_config_dir, fname))
        for step in repository.PROCESSING_STEPS:
            cdir = os.path.join(corpus_data_dir, step, '01', 'config')
            sdir = os.path.join(corpus_data_dir, step, '01', 'state')
            for fname in glob.glob(cdir + os.sep + '*'):
                target = os.path.join(self.corpus_data_dir,
                                      "%s-config-%s" % (step, os.path.basename(fname)))
                shutil.copyfile(fname, target)
            for fname in glob.glob(sdir + os.sep + '*'):
                target = os.path.join(self.corpus_data_dir,
                                      "%s-state-%s" % (step, os.path.basename(fname)))
                shutil.copyfile(fname, target)

    def create_index_from_corpus_data(self):
        with open(self.filelist_file, 'w') as fh:
            for line in open(os.path.join(self.corpus_config_dir, 'files.txt')):
                basename = os.path.basename(line.strip().split()[-1])
                (prefix, kind, id) = repository.get_patent_id(basename)
                path = repository.patentid2path(id)
                fh.write("%s\t%s%s%s\n" % (id, os.sep.join(path), os.sep, basename))

    def sources(self): return RepositoryIterator(self)

    def processed(self, step):
        if not step in repository.PROCESSING_STEPS:
            exit("WARNING: illegal step")
        return RepositoryIterator(self, step)

    def d1_txt(self): return RepositoryIterator(self, 'd1_txt')
    def d2_seg(self): return RepositoryIterator(self, 'd2_seg')
    def d2_tag(self): return RepositoryIterator(self, 'd2_tag')
    def d3_phr_feats(self): return RepositoryIterator(self, 'd3_phr_feats')

    def identifiers(self):
        """Return a list of all identifier-path pairs from the files.txt list."""
        ids = []
        with open(self.filelist_file) as fh:
            for line in fh:
                ids.append(line.split())
        #return ids[:20]
        return ids

    def analyze(self):
        """The files.txt list of a view contains files that may not occur in the
        repository, both sources and processed. This method prints the number of
        actual files in the repository pointed at by the view. Results are also
        written to disk in the info directory in a time-stamped file. This takes
        about 10-12 seconds for a view with 1000 elements (on a NFS share)"""
        t0 = time.time()
        self.info_dir = os.path.join(self.dir, 'info')
        if not os.path.exists(self.info_dir):
            os.makedirs(self.info_dir)
        info_file = os.path.join(self.info_dir, "info-%s.txt" % repository.timestamp())
        fh = open(info_file, 'w')
        counts = { 'sources': sum(1 for _ in self.sources()) }
        for step in repository.PROCESSING_STEPS:
            counts[step] = sum(1 for e in self.processed(step) if e)
        fh.write("%6d  sources\n" % counts['sources'])
        print "%6d  sources" % counts['sources']
        for step in repository.PROCESSING_STEPS:
            fh.write("%6d  %s\n" % (counts[step], step))
            print "%6d  %s" % (counts[step], step)
        print "Results written to", fh.name
        print "Processing time: %s seconds" % (time.time() - t0)


class RepositoryIterator(object):

    """Iterator objects to iterate over files in a repository given a view."""

    def __init__(self, view, step=None):
        self.repository = view.repository.dir
        self.path = "data/processed%s%s" %  (os.sep, step) if step else 'data/sources'
        self.ids = view.identifiers()

    def __iter__(self):
        return self

    def next(self):
        try:
            next = self.ids.pop(0)
            fname = os.path.join(self.repository, self.path, next[1] + '.gz')
            if os.path.exists(fname):
                return fname
            return None
        except IndexError:
            raise StopIteration

    def reset(self):
        self.ids = view.identifiers()



if __name__ == '__main__':

    options = ['initialize-from-corpus', 'corpus=', 'view=', 'analyze', 'repository=']
    (opts, args) = getopt.getopt(sys.argv[1:], 'r:v:c:', options)
    init_p, analyze_p = False, False
    repo, view, corpus = None, None, None
    for opt, val in opts:
        if opt == '--initialize-from-corpus': init_p = True
        if opt == '--analyze': analyze_p = True
        if opt in ('-r', '--repository'): repo = val
        if opt in ('-v', '--view'): view = val
        if opt in ('-c', '--corpus'): corpus = val

    if init_p:
        if view is None: exit("WARNING: no view defined")
        if corpus is None: exit("WARNING: no corpus defined")
        if repository is None: exit("WARNING: no repository defined")
        create_view_from_corpus(corpus, view, repo)

    elif analyze_p:
        if view is None: exit("WARNING: no view defined")
        view = View(view)
        view.analyze()
