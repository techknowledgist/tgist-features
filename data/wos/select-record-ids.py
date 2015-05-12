"""

Select identifers for a couple of subject domains

Input is in INDEX_DIR, in directories for each year.
Output is in SUBJECTS_DIR, with same structure as INDEX_DIR.

Creates files with subject groups (A01, A04, A06, A07 and A10) and record
identifiers. The identifiers are either the ones given by the <ut> tag in the
2012 data drop or the <UID> tag in the 2014 data drop, from which the 2013 data
were taken.

"""

import sys, os, glob, gzip, codecs, time

INDEX_DIR = 'index'
SUBJECTS_DIR = 'subject-lists'

# These are substrings manually derived from looking at the subject domains and
# all available subjects. If a subject matches one of the strings than the
# subject is part of the group Axx. Note that A07 includes A06 and the SOLAR
# MATERIALS subset of A08.
A01 = ['MULTIDISCIPLINARY']
A04 = ['PHYSICS,']
A06 = ['NANO']
A07 = ['NANO', 'MATERIALS', 'ENGINEERING']
A10 = ['BIOCHEMISTRY', 'GENETICS', 'BIOTECHNOLOGY', 'CELL BIOLOGY']



if __name__ == '__main__':

    for year in sorted(os.listdir(INDEX_DIR)):
        print year
        if not year == '2013':
            continue
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
                # the 2014 data drop uses mixed case
                subject = fields[5].upper()
                for t in A01:
                    if subject.find(t) > -1: out.write("A01 %s\n" % ut)
                for t in A04:
                    if subject.find(t) > -1: out.write("A04 %s\n" % ut)
                for t in A06:
                    if subject.find(t) > -1: out.write("A06 %s\n" % ut)
                for t in A07:
                    if subject.find(t) > -1: out.write("A07 %s\n" % ut)
                for t in A10:
                    if subject.find(t) > -1: out.write("A10 %s\n" % ut)
