# -*- coding: utf-8 -*-                                                                                                                         
# cn_sef2tag.py
# tag segmented chinese files
# formatted as follows:
# field headers of the form    FH_<name>:
# each followed by one or more lines of text (without any empty lines)
# A line can consist of multiple sentences, which will be split by the tagger
# Last line must be     END:

import sdp
import os
import codecs
import re

debug_p = False
#debug_p = True

# pattern to match a parenthesis and its tag (e.g. )_NN )
paren_tag = re.compile('([()])_[^\s]*' )

# replace all parenthesis tags in a tagger output line with the tag <paren>_PU
# This is needed to override the Stanford tagger's incorrect tagging of parens in 
# Chinese text.  Sometimes they are tagged as _NN, which would cause the chunker to
# include them as part of a noun phrase.
def fix_paren_tag(line):
    return(re.sub(paren_tag, r'\1_PU', line))

def tag(input, output, tagger):
    s_input = codecs.open(input, encoding='utf-8')
    s_output = open(output, "w")
    section = ""
    sent_no_in_section = 0
    for line in s_input:
        #line = line.strip("\n")
        if debug_p == True:
            print "[tag]Processing line: %s\n" % line
        if line != "":
            # note we leave the \n on the line for headers so they remain on a separate line
            # in the output.
            if line[0:3] == "FH_":
                # we are at a section header
                # write it back out as is
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

def test_tag_en():
    input = "/home/j/anick/fuse/data/patents/en_test/txt/US20110052365A1.xml"
    output = "/home/j/anick/fuse/data/patents/en_test/tag/US20110052365A1.xml"
    tagger = sdp.STagger("chinese.tagger")
    tag(input, output, tagger)


# cn_seg2tag.test_tag_cn()
def test_tag_cn():
    input = "/home/j/anick/fuse/data/patents/tmp/cn/CN1394959A-tf.seg"
    output = "/home/j/anick/fuse/data/patents/tmp/cn/CN1394959A-tf.tag"
    tagger = sdp.STagger("chinese.tagger")
    tag(input, output, tagger)


def txt2tag_file(txt_file, tag_file, tagger):
    tag(txt_file, tag_file, tagger)


# tag all txts in source and place results in target dir
def txt2tag_dir(source_path, target_path, tagger):
    for file in os.listdir(source_path):
        source_file = source_path + "/" + file
        target_file = target_path + "/" + file

        print "[txt2tag_dir]from %s to %s" % (source_file, target_file)
        #txt2tag_file(source_file, target_file, tagger)
        tag(source_file, target_file, tagger)
    print "[txt2tag_dir]done"


"""
Stanford tagger options:
(info here: http://ufallab.ms.mff.cuni.cz/tectomt/share/data/models/tagger/stanford/README-Models.txt)
chinese7.tagger
chinese7.tagger.props
chinese.tagger
chinese.tagger.props
english-bidirectional-distsim.tagger
english-bidirectional-distsim.tagger.props
english-caseless-left3words-distsim.tagger
english-caseless-left3words-distsim.tagger.props
english-left3words-distsim.tagger
english-left3words-distsim.tagger.props
french.tagger
french.tagger.props
german-dewac.tagger
german-dewac.tagger.props
german-fast.tagger
german-fast.tagger.props
german-hgc.tagger
german-hgc.tagger.props
"""

# language is en, de, cn
# lang_path (above year_dir)
# e.g. patent_txt2tag_dir("/home/j/anick/fuse/data/patents", "de")
def patent_txt2tag_dir(lang_path, language):
    # choose tagger for language
    if language == "en":
        tagger = sdp.STagger("english-caseless-left3words-distsim.tagger")
        txt_path = lang_path + "/" + language + "/txt"
    elif language == "de":
        # note: german-fast is much faster than german-dewac although 4% poorer in dealing
        # with unknown words.
        tagger = sdp.STagger("german-fast.tagger")
        txt_path = lang_path + "/" + language + "/txt"
    elif language == "cn":
        tagger = sdp.STagger("chinese.tagger")
        # note we use the segmented docs for chinese rather than the txt form
        txt_path = lang_path + "/" + language + "/seg"

    tag_path = lang_path + "/" + language + "/tag"
    for year in os.listdir(txt_path):
        txt_year_dir = txt_path + "/" + year
        tag_year_dir = tag_path + "/" + year
        print "[patent_txt2tag_dir]calling txt2tag for dir: %s" % txt_year_dir
        txt2tag_dir(txt_year_dir, tag_year_dir, tagger)
    print "[patent_txt2tag_dir]finished writing tagged data to %s" % tag_path

# top level call to tag txt data dir in a language
# txt2tag.tag_lang("en")
# txt2tag.tag_lang("de")
# cn_seg2tag.tag_lang("cn")
def tag_lang(lang):
    patent_path = "/home/j/anick/fuse/data/patents"
    patent_txt2tag_dir("/home/j/anick/fuse/data/patents", lang)
