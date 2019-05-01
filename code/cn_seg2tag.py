# -*- coding: utf-8 -*-

# cn_sef2tag.py
# tag segmented chinese files
# formatted as follows:
# field headers of the form    FH_<name>:
# each followed by one or more lines of text (without any empty lines)
# A line can consist of multiple sentences, which will be split by the tagger

import codecs
import re
import sdp

debug_p = False

# pattern to match a parenthesis and its tag (e.g. )_NN )
paren_tag = re.compile('([()])_[^\s]*')


class Tagger(object):

    def __init__(self):
        self.tagger = sdp.Tagger("chinese.tagger")

    def tag(self, file_in, file_out):
        tag(file_in, file_out, self.tagger)


# replace all parenthesis tags in a tagger output line with the tag <paren>_PU
# This is needed to override the Stanford tagger's incorrect tagging of parens in 
# Chinese text.  Sometimes they are tagged as _NN, which would cause the chunker to
# include them as part of a noun phrase.
def fix_paren_tag(line):
    return re.sub(paren_tag, r'\1_PU', line)


def tag(input_file, output_file, tagger):
    s_input = codecs.open(input_file, encoding='utf-8')
    s_output = open(output_file, "w")
    c = 0
    for line in s_input:
        c += 1
        if debug_p:
            print "[tag]Processing line: %s\n" % line
        if line != "":
            # note we leave the \n on the line for headers so they remain on a separate line
            # in the output.
            if line[0:3] == "FH_":
                # we are at a section header, write it back out as is
                line_out = line.encode('utf-8')
                s_output.write(line_out)
            else:
                line = line.strip("\n")
                if debug_p:
                    print "[tag]line: %s" % line
                # process the sentences in the section
                l_tag_string = tagger.tag(line)
                for tag_string in l_tag_string:
                    # replace all tags for parens with <paren>_PU
                    # (fixes a bug in the Stanford tagger)
                    tag_string = fix_paren_tag(tag_string)
                    tag_string = tag_string.encode('utf-8')
                    if debug_p:
                        print "[tag]tag_string: %s" % tag_string
                    s_output.write("%s\n" % tag_string)
    s_input.close()
    s_output.close()
