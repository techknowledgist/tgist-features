"""

Turn file lists into list that can serve as input for corpus creation.

This also makes sure that the files are listed in a random order.

Creates a new directory file-lists-corpus with the same structure as
file-lists. Overwrites what was in file-lists-corpus.


"""

import os, sys, glob, random

WOS_DIR = '/home/j/corpuswork/fuse/FUSEData/2013-04/wos'

IN_DIR = WOS_DIR + '/file-lists'
OUT_DIR = WOS_DIR + '/file-lists-corpus'

for fname in sorted(glob.glob(os.path.join(IN_DIR, '*', '*'))):
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
        fh_out.write("%s\t%s\t%s\n" %
                     (year, line.strip(), os.sep.join(line.strip().split(os.sep)[-2:])))
