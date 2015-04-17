"""

Select identifers for a couple of subject domains

Input is in INDEX_DIR, in directories for each year.
Output is in SUBJECTS_DIR, with same structure as INDEX_DIR.

Creates files with subject groups (A01, A04 and A10) and <ut> identifiers.

"""

import sys, os, glob, gzip, codecs, time

INDEX_DIR = 'index'
SUBJECTS_DIR = 'subject-lists'

# These are substrings manuallt derived from looking at the subject domains and
# all available subjects. If a subject matches one of the strings than the
# subject is part of the group Axx. There seems to be no good option for A06,
# Nanotechnology.
A01 = ['MULTIDISCIPLINARY']
A04 = ['PHYSICS,']
A10 = ['BIOCHEMISTRY', 'GENETICS', 'BIOTECHNOLOGY', 'CELL BIOLOGY']



if __name__ == '__main__':

    for year in sorted(os.listdir(INDEX_DIR)):
        print year
        if not os.path.exists(os.path.join(SUBJECTS_DIR, year)):
            os.makedirs(os.path.join(SUBJECTS_DIR, year))
        fnames = glob.glob(os.path.join(INDEX_DIR, year) + os.sep + 'index-main-*')
        for fname in sorted(fnames):
            print '  ', fname
            outfname = os.path.basename(fname)[11:]
            out = open(os.path.join(SUBJECTS_DIR, year, outfname), 'w')
            for line in open(fname):
                fields = line.split("\t")
                ut = fields[0]
                subject = fields[5]
                for t in A01:
                    if subject.find(t) > -1: out.write("A01 %s\n" % ut)
                for t in A04:
                    if subject.find(t) > -1: out.write("A04 %s\n" % ut)
                for t in A10:
                    if subject.find(t) > -1: out.write("A10 %s\n" % ut)

