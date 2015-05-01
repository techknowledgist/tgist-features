"""

Print a list of the values in the FH_SUBJECTS section of the d1_txt documents in
a corpus.

Usage:

    python get-subjects.py CORPUS_PATH

Results are written to standard output.

"""


import os, sys, codecs, gzip


def get_subject(fname):
    subject = False
    gzipfile = gzip.open(fname + '.gz', 'rb')
    reader = codecs.getreader('utf-8')
    fh = reader(gzipfile)
    for line in fh:
        if line.startswith('FH_SUBJECT'):
            subject = True
        elif line.startswith('FH'):
            subject = False
        elif subject:
            return line.strip()


corpus = sys.argv[1]

subjects = {}
for line in open(os.path.join(corpus, 'config', 'files.txt')):
    fname = line.strip().split("\t")[-1]
    fname = os.path.join(corpus, 'data', 'd1_txt', '01', 'files', fname)
    subject = get_subject(fname)
    subjects[subject] = subjects.get(subject,0) + 1
for subj in sorted(subjects.keys()):
    print "%5d  %s" % (subjects[subj], subj)
