"""collect_terms.py

Collect the terms in a corpus.

Usage:

    $ python collect_terms.py CORPUS_PATH TERMS_FILE FILELIST?

The CORPUS_PATH holds a corpus as created by the script step2_process.py in
ontology/doc_processing. The third argument is optional and can be used to
select a non-standard file list (files.txt is the default).

Prints the terms with their frequencies, and ordered alphabetically, to
TERMS_FILE.

Examples:

    $ setenv CORPORA /home/j/corpuswork/fuse/FUSEData/corpora/ln-cn-all-600k/subcorpora
    $ setenv TERMS /home/j/corpuswork/fuse/FUSEData/corpora/ln-cn-all-600k/terms
    $ python collect_terms.py $CORPORA/1995 $TERMS/1995-terms.txt
    $ python collect_terms.py $CORPORA/2008 $TERMS/2008-terms.txt files-20k.txt

"""


import os, sys, time, codecs
sys.path.append(os.path.abspath('../../../..'))
from ontology.utils.file import open_input_file

FILELIST = "files.txt"

def collect_terms_in_corpus(corpus):
    t1 = time.time()
    terms = {}
    done = 0
    for line in open(os.path.join(corpus, 'config', FILELIST)):
        done += 1
        if done % 100 == 0: print done
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

    corpus = sys.argv[1]
    terms_file = sys.argv[2]
    if len(sys.argv) > 3:
        FILELIST = sys.argv[3]
    terms = collect_terms_in_corpus(corpus)
    print_terms(terms, terms_file)
