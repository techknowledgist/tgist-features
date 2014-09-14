# tag2chunk.py

# TODO: remove __ from front of chunks in phr_feats

# for chunks doc (identify all chunks in a doc and output two files, 
# one with all chunks indexed by id with all features for that phrase occurrence (phr_feats)
# one with only chunk and <id><tab><bracketed sentence>, to be used for annotation)

import os, sys
import codecs
import sentence

sys.path.append(os.path.abspath('../..'))
from ontology.utils.file import open_input_file, open_output_file

# returns True if lists share at least one term
def share_term_p(l1, l2):
    for term in l1:
        if term in l2:
            return True
    return False

# symbol without blanks, with name and value separated by "__"
# name should be a string without blanks
# value should be a string and may contain blanks
def mallet_feature(name, value):
    value_separator = "="
    if value == "":
        return("")
    else:
        symbol = value.strip(" ").replace(" ", "_")
        feature = name + value_separator + symbol
        #print "created feature: %s" % feature
        return(feature)
    

class Doc:

    def __init__(self, tag_file, phr_feats_file, year, lang,
                 filter_p=True, chunker_rules='en', compress=True):
        
        self.input = tag_file
        self.output = phr_feats_file
        self.year = year
        self.chunk_schema = sentence.chunk_schema(chunker_rules)
        self.lang = lang
        self.compress = compress
        # field_name to list of sent instances
        # field name is header string without FH_ or : affixes
        self.d_field = {}

        # sent id to sent instance and chunk id to chunk instance
        self.d_sent = {}
        self.d_chunk = {}
        self.next_sent_id = 0
        self.next_chunk_id = 0

        # lc noun tokens appearing in title
        self.l_lc_title_noun = []

        # create the chunks
        self.process_doc(filter_p, chunker_rules)
        

    def process_doc(self, filter_p=True, chunker_rules='en'):

        """Process the doc, creating all potential technology chunks and
        calculating their features."""

        debug_p = False
        if debug_p:
            print "[process_doc] filter_p: %s, writing to %s" % \
                  (filter_p, self.output)
        s_input = open_input_file(self.input)
        s_output = open_output_file(self.output, compress=self.compress)
        section = "FH_NONE"   # default section if document has no section header lines
        self.d_field[section] = []

        sent_no_in_section = 0
        for line in s_input:
            line = line.strip("\n")
            if debug_p:
                print "[process_doc] line: %s" % line

            if line[0:3] == "FH_":
                # we are at a section header; note we have to strip off both
                # final ':' and whitespace, since in some cases eg. Chinese
                # segmentation, the colon will be separated from the header term
                # by a blank.
                section = line.split("_")[1].rstrip(": ")
                self.d_field[section] = []
                sent_no_in_section = 0

            else:
                # process the sentence, the line is a list of token_tag pairs
                if section == "TITLE" or section == "ABSTRACT":
                    self.l_lc_title_noun.extend(lc_nouns(line))

                # call the appropriate Sentence subclass based on the language
                sent_args = [self.next_sent_id, section, sent_no_in_section, line,
                             self.chunk_schema]
                sent = sentence.get_sentence_for_lang(self.lang, sent_args)
                # get context info
                i = 0
                for chunk in sent.chunk_iter():
                    if chunk.label == "tech":
                        # index of chunk start in sentence => ci
                        ci = chunk.chunk_start
                        hsent = sent.highlight_chunk(i)
                        mallet_feature_list = get_features(sent, ci)
                        mallet_feature_list.sort()
                        uid = os.path.basename(self.input) + "_" + str(self.next_chunk_id)
                        metadata_list = [uid, self.year, chunk.phrase.lower()]
                        if debug_p:
                            print "index: %i, start: %i, end: %i, sentence: %s" % \
                                (i, chunk.chunk_start, chunk.chunk_end, sent.sentence)
                        if add_chunk_data(self, chunk, section, filter_p):
                            add_line_to_phr_feats(metadata_list, mallet_feature_list,
                                                  s_output)
                        chunk.sid = self.next_sent_id
                        self.d_chunk[self.next_chunk_id] = chunk
                        sent.chunks.append(chunk)
                        self.next_chunk_id += 1
                    i = chunk.chunk_end
                    
                # keep track of the location of this sentence within the section
                sent_no_in_section += 1
                self.d_field[section].append(sent)
                self.d_sent[self.next_sent_id] = sent
                self.next_sent_id += 1

        s_input.close()
        s_output.close()


def get_features(sent, ci):
    """Call all feature_methods for the current sentence and create a list of their
    results, these are unbound methods, so must supply instance."""
    mallet_feature_list = [method(sent, ci) for method in sent.feature_methods]
    mallet_feature_list = [feat for feat in mallet_feature_list if feat is not None]
    return mallet_feature_list

def add_chunk_data(doc, chunk, section, filter_p):
    """FILTERING technology terms to output (if filter_p is True). We only output terms
    that are in the title or share a term with a title term.  Note that our 'title terms'
    can actually come from title or abstract. Many German patent titles are only one word
    long! This filter may need adjustment (e.g. for German compound terms, which may not
    match exactly, fitering ought to be based on component terms, not the compound as a
    whole).  Filtering is not applied if filter_p parameter is False. """
    return not filter_p \
           or (section == "TITLE" or share_term_p(doc.l_lc_title_noun, chunk.lc_tokens))

def add_line_to_phr_occ(uid, doc, chunk, hsent, s_output_phr_occ):
    """Write out the phrase occurrence data to phr_occ. For each phrase occurrence,
    include uid, year, phrase and full sentence (with highlighted chunk)."""
    #print "matched term for %s and %s" % (self.l_lc_title_noun, chunk.lc_tokens)
    unlabeled_out = u"\t".join([uid, doc.year, chunk.phrase.lower(), hsent + '\n'])
    s_output_phr_occ.write(unlabeled_out)

def add_line_to_phr_feats(metadata_list, mallet_feature_list, s_output_phr_feats):
    """Create a tab separated string of features to be written out to phr_feats. The full
     line includes metadata followed by features."""
    # meta data to go at beginning of phr_feats output lines
    metadata_list.extend(mallet_feature_list)
    full_list = metadata_list
    mallet_feature_string = u"\t".join(full_list) + '\n'
    #print "mallet_feature string: %s" % mallet_feature_string
    s_output_phr_feats.write(mallet_feature_string)

def tag2chunk_dir(tag_dir, phr_occ_dir, phr_feats_dir, year, lang, filter_p = True):
    for file in os.listdir(tag_dir):
        input = tag_dir + "/" + file
        output_phr_occ = phr_occ_dir + "/" + file
        output_phr_feats = phr_feats_dir + "/" + file
        doc = Doc(input, output_phr_occ, output_phr_feats, year, lang, filter_p)


# new3 output after changing chunker on 1/3/13  PGA
# tag2chunk.test_t2c()
def test_t2c():
    #input = "/home/j/anick/fuse/data/patents/en_test/tag/US20110052365A1.xml"
    #output_phr_occ = "/home/j/anick/fuse/data/patents/en_test/phr_occ/US20110052365A1.new3.xml"
    #output_phr_feats = "/home/j/anick/fuse/data/patents/en_test/phr_feats/US20110052365A1.new3.xml"

    input = "/home/j/anick/fuse/data/patents/en_test/tag/mini.xml"
    output_phr_occ = "/home/j/anick/fuse/data/patents/en_test/phr_occ/mini.new3.xml"
    output_phr_feats = "/home/j/anick/fuse/data/patents/en_test/phr_feats/mini.new3.xml"
    """ To test output:
    cat /home/j/anick/fuse/data/patents/en_test/phr_feats/mini.new3.xml | cut -f3 | more
    devicea
    deviceb
    testa
    testb
    mechanical testc
    mechanical testd
    picking up optical elements
    suction membera
    suction memberb
    suction memberc
    vacuum pump unit
    liquid spraying unit
    end
    """

    #cs = sentence.chunk_schema("en")
    year = "1980"
    lang = "en"
    #filter_p = True
    filter_p = False

    doc = Doc(input, output_phr_occ, output_phr_feats, year, lang, filter_p)
    return(doc)


# tag2chunk.test_t2c_de(True)
def test_t2c_de(filter_p):
    input = "/home/j/anick/fuse/data/patents/de/tag/1982/DE3102424A1.xml"
    output_phr_occ = "/home/j/anick/fuse/data/patents/de_test/DE3102424A1.phr_occ"
    output_phr_feats = "/home/j/anick/fuse/data/patents/de_test/DE3102424A1.phr_feats"
    cs = sentence.chunk_schema("de")
    year = "1980"
    lang = "de"
    #filter_p = True
    #filter_p = False
    doc = Doc(input, output_phr_occ, output_phr_feats, year, lang, filter_p)
    return(doc)

# tag2chunk.test_t2c_de_tag_sig()
def test_t2c_de_tag_sig():
    input = "/home/j/anick/fuse/data/patents/de_test/tag_sig_test.xml"
    output_phr_occ = "/home/j/anick/fuse/data/patents/de_test/tag_sig_test.phr_occ"
    output_phr_feats = "/home/j/anick/fuse/data/patents/de_test/tag_sig_test.phr_feats"
    cs = sentence.chunk_schema("de")
    year = "1982"
    lang = "de"
    doc = Doc(input, output_phr_occ, output_phr_feats, year, lang)
    return(doc)

# tag2chunk.test_t2c_cn()
def test_t2c_cn():
    input = "/home/j/anick/fuse/data/patents/tmp/cn/CN1394959A-tf.tag"
    output_phr_occ = "/home/j/anick/fuse/data/patents/cn_test/CN1394959A-tf.new.phr_occ"
    output_phr_feats = "/home/j/anick/fuse/data/patents/cn_test/CN1394959A-tf.new.phr_feats"
    year = "1980"
    lang = "cn"
    doc = Doc(input, output_phr_occ, output_phr_feats, year, lang)
    return(doc)

# returns (lowercased) nouns in a tag_string
def lc_nouns(tag_string):
    l_lc_nouns = []
    for tagged_token in tag_string.split(" "):
        (tok, tag) = tagged_token.rsplit("_", 1)
        if tag[0:1] == "N":
            l_lc_nouns.append(tok.lower())
    return(l_lc_nouns)

# language is en, de, cn
# lang_path (above year_dir)
# e.g. tag2chunk.patent_tag2chunk_dir("/home/j/anick/fuse/data/patents", "de")
def patent_tag2chunk_dir(patent_path, language, filter_p = True):
    lang_path = patent_path + "/" + language
    phr_occ_path = lang_path + "/phr_occ"
    phr_feats_path = lang_path + "/phr_feats"
    tag_path = lang_path + "/tag"
    c_schema = sentence.chunk_schema(language)
    for year in os.listdir(tag_path):
        phr_occ_year_dir = phr_occ_path + "/" + year
        phr_feats_year_dir = phr_feats_path + "/" + year
        tag_year_dir = tag_path + "/" + year
        print "[patent_tag2chunk_dir]calling tag2chunk, filter_p: %s, output dirs: %s, %s" \
              % (filter_p, phr_feats_year_dir, phr_occ_year_dir)
        tag2chunk_dir(tag_year_dir, phr_occ_year_dir, phr_feats_year_dir, year, language, filter_p)
    print "[patent_tag2chunk_dir]finished writing chunked data to %s and %s" % (phr_occ_path, phr_feats_path)

### debugging _no output produced PGA 10/8
def pipeline_tag2chunk_dir(root, language, filter_p = True):
    
    phr_occ_path = root + "/phr_occ"
    phr_feats_path = root + "/phr_feats"
    tag_path = root + "/tag"
    #c_schema = sentence.chunk_schema(language)
    # The only way to determine the year for a file is to look in file_list.txt
    d_file2year = {}
    file_list_file = os.path.join(root, "file_list.txt")
    s_list = open(file_list_file)
    year = ""
    file_path = ""
    for line in s_list:
        (id, year, path) = line.split(" ")
        # create the file name from id + .xml
        file_name = id + ".xml"
        tag_file = os.path.join(root, "tag", file_name)
        output_phr_occ = os.path.join(root, "phr_occ", file_name)
        output_phr_feats = os.path.join(root, "phr_feats", file_name)
        print "[pipeline_tag2chunk_dir]about to process doc: %s, phr_occ: %s, phr_feats: %s, year: %s" \
              % (tag_file, output_phr_occ, output_phr_feats, year)
        doc = Doc(tag_file, output_phr_occ, output_phr_feats, year, language, filter_p)
    s_list.close()
    print "[pipeline_tag2chunk_dir]finished writing chunked data to %s and %s" % (phr_occ_path, phr_feats_path)


# top level call to tag txt data dir in a language
# tag2chunk.chunk_lang("en")
# tag2chunk.chunk_lang("de")
# tag2chunk.chunk_lang("cn")
def chunk_lang(lang, filter_p = True):
    patent_path = "/home/j/anick/fuse/data/patents"
    patent_tag2chunk_dir("/home/j/anick/fuse/data/patents", lang, filter_p)


