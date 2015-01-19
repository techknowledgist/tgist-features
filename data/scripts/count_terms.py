"""count_terms.py

Counts the number of terms and technologies in a corpus.

Usage:

    $ python count_terms.py TERMS_FILE

The TERMS_FILE holds the result of the collect_terms.py script, that is, a list
of tab-sepated frequency-term pairs. The total number of term types and term
instances is printed to the standards output.

If TERMS_FILE is enclosed in double quotes and contains unix wild cards, then
counts are printed for each file that the TERMS_FILE expression covers.

Examples:

    $ setenv TERMS /home/j/corpuswork/fuse/FUSEData/corpora/ln-cn-all-600k/terms
    $ python count_terms.py $TERMS/ln-cn-all-600k-1995-terms.txt
    $ python count_terms.py "$TERMS/ln-cn-all-600k-199?-terms.txt"

"""

import os, sys, codecs, glob

CORPUS = '../patents/corpora/sample-us'

def count_terms(terms_file):
    type_count = 0
    token_count = 0
    for line in codecs.open(terms_file):
        freq, term = line.split("\t")
        freq = int(freq)
        type_count += 1
        token_count += freq
    basename = os.path.basename(terms_file)
    print "%s\t%8d\t%8d" % (basename, type_count, token_count)

if __name__ == '__main__':
    terms_file = sys.argv[1]
    for terms_file in sorted(glob.glob(sys.argv[1])):
        count_terms(terms_file)
