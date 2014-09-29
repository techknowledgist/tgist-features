"""count_tokens.py

Counts the number of files, sentences and tokens in a corpus.

Usage:

    $ python count_tokens.py CORPUS_PATH

The CORPUS_PATH holds a corpus as created by the script step2_process.py in
ontology/doc_processing. The default for CORPUS_PATH is the example corpus.

Prints the file count, sentence count and token count to the standard output.

It takes about 10 minutes to run this scripts on a 6MB, 500K token corpus. You
would obviously never run this to just get the number of files.

"""


import os, sys, time

sys.path.append(os.path.abspath('../../../..'))
from ontology.utils.file import open_input_file


CORPUS = '../patents/corpora/sample-us'


def count_tokens_in_corpus(corpus):
    t1 = time.time()
    file_count = 0
    sentence_count = 0
    token_count = 0
    done = 0
    for line in open(os.path.join(corpus, 'config', 'files.txt')):
        #if done >= 100: break
        fname = line.split()[2]
        fname = os.path.join(corpus, 'data', 'd2_tag', '01', 'files', fname)
        file_count += 1
        for line in open_input_file(fname):
            sentence_count += 1
            token_count += len(line.split())
        done += 1
    print corpus, file_count, sentence_count, token_count, "(%d seconds)" \
          % (time.time() - t1)


if __name__ == '__main__':

    if len(sys.argv) > 1:
        CORPUS = sys.argv[1]
    count_tokens_in_corpus(CORPUS)
