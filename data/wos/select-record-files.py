"""

Select records from WoS archives given a list of identifiers for some subjects.

To build A01, A04, A07 and A10 corpora in corpora/ for 1995:

    python select-record-files.py 1995

The identifiers are pulled from subject-lists.

The structure of the corpus is as follows:

    	corpora/A01
	corpora/A01/1995
	corpora/A01/1995/WoS.out.1995000024
	corpora/A01/1995/WoS.out.1995000024/A1994BC72Q00010.xml
	corpora/A01/1995/WoS.out.1995000024/A1994BC72Q00001.xml
	corpora/A01/1995/WoS.out.1995000024/A1994BC72Q00012.xml

Note that A06 is not built because it is so tiny.

This works for both the 2012 and 2014 data drop format.

"""


import sys, os, gzip, codecs, time

# this is overruled if the year is 2013
WOS_DIR = '/home/j/corpuswork/fuse/FUSEData/2013-04/WoS_2012_Aug'

SUBJECTS_DIR = 'subject-lists'

# it is much faster when you run this on a local disk and then move it to
# corpuswork
TARGET_DIR = "/home/j/corpuswork/fuse/FUSEData/2013-04/wos/extracted"
TARGET_DIR = "corpora"

A01_DIR = os.path.join(TARGET_DIR, 'A01')
A04_DIR = os.path.join(TARGET_DIR, 'A04')
A07_DIR = os.path.join(TARGET_DIR, 'A07')
A10_DIR = os.path.join(TARGET_DIR, 'A10')


def select(year, fname):

    print year, fname

    A01, A04, A07, A10 = read_subjects(year, fname)
    archive = os.path.join(WOS_DIR, fname[:-4] + '.gz')
    gzipfile = gzip.open(os.path.join(WOS_DIR, archive), 'rb')
    fh = codecs.getreader('utf-8')(gzipfile)

    A01_subdir = os.path.join(A01_DIR, year, fname[:-4])
    if not os.path.exists(A01_subdir): os.makedirs(A01_subdir)

    A04_subdir = os.path.join(A04_DIR, year, fname[:-4])
    if not os.path.exists(A04_subdir): os.makedirs(A04_subdir)

    A07_subdir = os.path.join(A07_DIR, year, fname[:-4])
    if not os.path.exists(A07_subdir): os.makedirs(A07_subdir)

    A10_subdir = os.path.join(A10_DIR, year, fname[:-4])
    if not os.path.exists(A10_subdir): os.makedirs(A10_subdir)

    recs = 0
    rec = []
    ut = None
    isA01, isA04, isA07, isA10 = False, False, False, False
    for line in fh:
        # for the 2012 and 2014 format
        if line.startswith('<REC') or line.startswith('<REC '):
            recs += 1
            rec = []
            ut = None
            isA01, isA04, isA07, isA10 = False, False, False, False
        # for the 2012 format
        elif line.startswith('<ut>'):
            rec.append(line)
            ut = line.split('>')[1].split('<')[0]
            if ut in A01: isA01 = True
            elif ut in A04: isA04 = True
            elif ut in A07: isA07 = True
            elif ut in A10: isA10 = True
        # for the 2014 format
        elif line.startswith('<UID>'):
            rec.append(line)
            ut = line.split('>')[1].split('<')[0]
            if ut in A01: isA01 = True
            elif ut in A04: isA04 = True
            elif ut in A07: isA07 = True
            elif ut in A10: isA10 = True
        elif line.startswith('</REC>'):
            if isA01: create_file('A01', A01_subdir, ut, rec)
            elif isA04: create_file('A04', A04_subdir, ut, rec)
            elif isA07: create_file('A07', A07_subdir, ut, rec)
            elif isA10: create_file('A10', A10_subdir, ut, rec)
        else:
            rec.append(line)
            #if recs > 10: exit()


def read_subjects(year, fname):
    subjects_list = os.path.join(SUBJECTS_DIR, year, fname)
    A01 = {}
    A04 = {}
    A07 = {}
    A10 = {}
    for line in open(subjects_list):
        subj, ut = line.split()
        if subj == 'A01': A01[ut] = True
        elif subj == 'A04': A04[ut] = True
        elif subj == 'A07': A07[ut] = True
        elif subj == 'A10': A10[ut] = True
    return A01, A04, A07, A10

def create_file(domain, dir, ut, rec):
    #if not domain == 'A07':
    #    return
    fh = codecs.open(os.path.join(dir, ut + '.xml'), 'w', encoding='utf8')
    fh.write("<REC>\n%s</REC>\n" % ''.join(rec))



if __name__ == '__main__':

    year = sys.argv[1]
    if year == '2013':
        WOS_DIR = '/home/j/corpuswork/fuse/FUSEData/2013-04/WoS_2014_Aug'
    for fname in sorted(os.listdir(os.path.join(SUBJECTS_DIR, year))):
        select(year, fname)
