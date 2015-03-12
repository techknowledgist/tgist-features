"""view.py

Interface to views.

"""

import os, shutil, glob
import repository


def create_view(view_dir, repository_dir):
    """Create a new empty view in directory view_dir and hook it up to the
    repository in repository_dir."""
    if os.path.exists(view_dir):
        exit("Directory '%s' already exists." % self.dir)
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
        with open(self.repository_file) as fh:
            self.repository = repository.Repository(fh.read().strip())

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
        pass



if __name__ == '__main__':

    corpus = '/home/j/corpuswork/fuse/FUSEData/corpora/ln-us-A21-computers/subcorpora/1997'
    view = 'z-view-test'
    create_view_from_corpus(corpus, view, 'ln-us')
