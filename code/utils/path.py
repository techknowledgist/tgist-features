import os, sys, errno, stat, subprocess, gzip, codecs


def read_only(filename):
    """Set permissions on filename to read only."""
    os.chmod(filename, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


def make_writable(filename):
    """Make filename writable by owner."""
    os.chmod(filename, stat.S_IWRITE | stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


def open_input_file(filename):
    """First checks whether there is a gzipped version of filename, if so, it
    returns a StreamReader instance. Otherwise, filename is a regular
    uncompressed file and a file object is returned."""
    # TODO: generalize this over reading and writing (or create two methods)
    # print "[file.py in open_input_file] filename: %s" % filename
    if os.path.exists(filename + '.gz'):
        # print "file.py: in if, filename: %s" % (filename + '.gz')
        gzipfile = gzip.open(filename + '.gz', 'rb')
        reader = codecs.getreader('utf-8')
        return reader(gzipfile)
    elif os.path.exists(filename):
        # fallback case, possibly needed for older runs
        return codecs.open(filename, encoding='utf-8')
    else: 
        print "[file.py open_input_file] file does not exist: %s" % filename


def open_output_file(fname, compress=True):
    """Return a StreamWriter instance on the gzip file object if compress is
    True, otherwise return a file object."""
    if compress:
        if fname.endswith('.gz'):
            gzipfile = gzip.open(fname, 'wb')
        else:
            gzipfile = gzip.open(fname + '.gz', 'wb')
        writer = codecs.getwriter('utf-8')
        return writer(gzipfile)
    else:
        return codecs.open(fname, 'w', encoding='utf-8')


def ensure_path(path, verbose=False):
    """Make sure path exists."""
    try:
        os.makedirs(path)
        if verbose:
            print "[ensure_path] created %s" % path
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def get_file_paths(source_path):
    """Return a list with all filenames in source_path."""
    file_paths = []
    for (root, dirs, files) in os.walk(source_path):
        for file in files:
            file_paths.append(os.path.join(root, file))
    return file_paths


def create_file(filename, content=None):
    """Create a file with name filename and write content to it if any was given."""
    fh = open(filename, 'w')
    if content is not None:
        fh.write(content)
    fh.close()


def compress(*fnames):
    """Compress all filenames fname in *fnames using gzip. Checks first if the
    file was already compressed."""
    for fname in fnames:
        if fname.endswith(".gz"):
            continue
        if os.path.exists(fname + '.gz'):
            continue
        subprocess.call(['gzip', fname])


def uncompress(*fnames):
    """Uncompress all files fname in *fnames using gunzip. The fname argument
    does not include the .gz extension, it is added by this function. If a file
    fname already exists, the function will not attempt to uncompress."""
    for fname in fnames:
        if not os.path.exists(fname):
            subprocess.call(['gunzip', fname + '.gz'])
