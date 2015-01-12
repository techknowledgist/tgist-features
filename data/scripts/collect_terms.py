"""collect_terms.py

Collect the terms in a corpus.

Usage:

    $ python collect_terms.py CORPUS_PATH TERMS_FILE

The CORPUS_PATH holds a corpus as created by the script step2_process.py in
ontology/doc_processing. The default for CORPUS_PATH is the example corpus.

Prints the terms with their frequencies, and ordered alphabetically, to
TERMS_FILE.


"""


import os, sys, time, codecs
sys.path.append(os.path.abspath('../../../..'))
from ontology.utils.file import open_input_file


def collect_terms_in_corpus(corpus):
    t1 = time.time()
    terms = {}
    for line in open(os.path.join(corpus, 'config', 'files.txt')):
        #if done >= 100: break
        fname = line.split()[2]
        fname = os.path.join(corpus, 'data', 'd3_phr_feats', '01', 'files', fname)
        for line in open_input_file(fname):
            term = line.split("\t")[2]
            terms[term] = terms.get(term,0) + 1
    return terms

def print_terms(terms, outfile):
    fh = codecs.open(outfile, 'w', encoding='utf8')
    for term in sorted(terms):
        fh.write("%d\t%s\n" % (terms[term], term))


if __name__ == '__main__':

    if len(sys.argv) > 1:
        CORPUS = sys.argv[1]
    terms = collect_terms_in_corpus(sys.argv[1])
    print_terms(terms, sys.argv[2])
