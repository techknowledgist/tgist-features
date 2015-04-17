"""

Select records from WoS archives given a list of identifiers for some subjects.

To build A01, A04 and A10 corpora in corpora/ for 1995:

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

"""


import sys, os, gzip, codecs, time

WOS_DIR = '/home/j/corpuswork/fuse/FUSEData/2013-04/WoS_2012_Aug'

SUBJECTS_DIR = 'subject-lists'

A01_DIR = 'corpora/A01'
A04_DIR = 'corpora/A04'
A10_DIR = 'corpora/A10'



def select(year, fname):

    print year, fname

    A01, A04, A10 = read_subjects(year, fname)
    archive = os.path.join(WOS_DIR, fname[:-4] + '.gz')
    gzipfile = gzip.open(os.path.join(WOS_DIR, archive), 'rb')
    fh = codecs.getreader('utf-8')(gzipfile)

    A01_subdir = os.path.join(A01_DIR, year, fname[:-4])
    if not os.path.exists(A01_subdir): os.makedirs(A01_subdir)

    A04_subdir = os.path.join(A04_DIR, year, fname[:-4])
    if not os.path.exists(A04_subdir): os.makedirs(A04_subdir)
    
    A10_subdir = os.path.join(A10_DIR, year, fname[:-4])
    if not os.path.exists(A10_subdir): os.makedirs(A10_subdir)

    recs = 0
    rec = []
    ut = None
    isA01, isA04, isA10 = False, False, False
    for line in fh:
        if line.startswith('<REC>'):
            recs += 1
            rec = []
            ut = None
            isA01, isA04, isA10 = False, False, False
        elif line.startswith('<ut>'):
            rec.append(line)
            ut = line.split('>')[1].split('<')[0]
            if ut in A01: isA01 = True
            elif ut in A04: isA04 = True
            elif ut in A10: isA10 = True
        elif line.startswith('</REC>'):
            if isA01: create_file(A01_subdir, ut, rec)
            elif isA04: create_file(A04_subdir, ut, rec)
            elif isA10: create_file(A10_subdir, ut, rec)
        else:
            rec.append(line)
            #if recs > 10: exit()


def read_subjects(year, fname):
    subjects_list = os.path.join(SUBJECTS_DIR, year, fname)
    A01 = {}
    A04 = {}
    A10 = {}
    for line in open(subjects_list):
        subj, ut = line.split()
        if subj == 'A01': A01[ut] = True
        elif subj == 'A04': A04[ut] = True
        elif subj == 'A10': A10[ut] = True
    return A01, A04, A10

def create_file(dir, ut, rec):
    fh = codecs.open(os.path.join(dir, ut + '.xml'), 'w', encoding='utf8')
    fh.write("<REC>\n%s</REC>\n" % ''.join(rec))



if __name__ == '__main__':

    year = sys.argv[1]
    for fname in sorted(os.listdir(os.path.join(SUBJECTS_DIR, year))):
        select(year, fname)
