"""

Turn file lists into list that can serve as input for corpus creation.

Creates a new directory file-lists-corpus with the same structure as
file-lists. Over writes what was in file-lists-corpus.


"""

import os, sys, glob

IN_DIR = 'file-lists'
OUT_DIR = 'file-lists-corpus'

for fname in glob.glob(os.path.join(IN_DIR, '*', '*')):
    print fname
    (prefix, domain, basename) = fname.split(os.sep)
    domain_dir = os.path.join(OUT_DIR, domain)
    if not os.path.isdir(domain_dir):
        os.makedirs(domain_dir)
    outfile = os.path.join(domain_dir, basename)
    fh_in = open(fname)
    fh_out = open(outfile, 'w')
    for line in fh_in:
        year = line.split(os.sep)[-2][8:12]
        fh_out.write("%s\t%s\t%s\n" %
                     (year, line.strip(), os.sep.join(line.strip().split(os.sep)[-2:])))
