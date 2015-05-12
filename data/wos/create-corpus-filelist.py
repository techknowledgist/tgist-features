"""

Turn file lists into list that can serve as input for corpus creation.

This also makes sure that the files are listed in a random order.

Usage:

    python create-corpus-filelist.py YEAR?

    The YEAR is optional, if it is given only file lists from that year will be
    processed.

Creates a new directory file-lists-corpus with the same structure as
file-lists. Overwrites what was in file-lists-corpus.

File lists are expected to be in /home/j/corpuswork/fuse/FUSEData/2013-04/wos,
namely in file-lists and file-lists-corpus.

"""

import os, sys, glob, random

WOS_DIR = '/home/j/corpuswork/fuse/FUSEData/2013-04/wos'

IN_DIR = WOS_DIR + '/file-lists'
OUT_DIR = WOS_DIR + '/file-lists-corpus'

YEAR = None

if len(sys.argv) > 1:
    YEAR = sys.argv[1]
    
for fname in sorted(glob.glob(os.path.join(IN_DIR, '*', '*'))):
    if YEAR is not None and not fname.endswith(YEAR+'.txt'):
        continue
    print fname
    path = fname.split(os.sep)
    domain = path[-2]
    basename = path[-1]
    domain_dir = os.path.join(OUT_DIR, domain)
    if not os.path.isdir(domain_dir):
        os.makedirs(domain_dir)
    outfile = os.path.join(domain_dir, basename)
    fh_in = open(fname)
    fh_out = open(outfile, 'w')
    lines = fh_in.readlines()
    random.shuffle(lines)
    for line in lines:
        year = line.split(os.sep)[-2][8:12]
        # let this overrule what is in the file name
        if YEAR is not None:
            year = YEAR
        longpath = line.strip()
        shortpath = os.sep.join(line.strip().split(os.sep)[-2:])
        if longpath. endswith('.gz'): longpath = longpath[:-3]
        if shortpath. endswith('.gz'): shortpath = shortpath[:-3]
        fh_out.write("%s\t%s\t%s\n" % (year, longpath, shortpath))
