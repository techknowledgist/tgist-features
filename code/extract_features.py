"""Extract features from a processed corpus

Utility script that takes all the files in a corpus and extracts the feature
vectors in the d3_feats data set.

Usage:

    $ python extract_features CORPUS_DIRECTORY OUTPUT_FILE

All features are written to OUTPUT_FILE which is organized as follows:

    <file-path-1>
        <feature-vector-1>
        <feature-vector-2>
        <feature-vector-3>
        ...
    <file-path-2>
        <feature-vector-1>
        <feature-vector-2>
        <feature-vector-3>
        ...

The feature vectors are exactly as in the orignal d3_feats files in the corpus,
but note that they are prefixed with a tab.

"""


import os, sys

from corpus import Corpus
from utils.path import open_input_file, open_output_file


if __name__ == '__main__':

    corpus_path = sys.argv[1]
    output = sys.argv[2]
    out = open_output_file(output, compress=True)

    data_set = os.path.join(corpus_path, 'data', 'd3_feats', '01', 'files')
    corpus = Corpus(None, None, None, None, corpus_path, None, None)

    count = 0
    for line in open(corpus.file_list):
        filename = line.strip().split()[2]
        count += 1
        if count % 100 == 0:
            print "%6d  %s" % (count, filename)
        fh = open_input_file(os.path.join(data_set, filename))
        out.write("%s\n" % filename)
        for line in fh:
            out.write("\t%s" % line)
        fh.close()
    out.close()
