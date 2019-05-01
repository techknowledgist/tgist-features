# tag2chunk.py

# TODO: remove __ from front of chunks in phr_feats

# for chunks doc (identify all chunks in a doc and output two files, 
# one with all chunks indexed by id with all features for that phrase occurrence (phr_feats)
# one with only chunk and <id><tab><bracketed sentence>, to be used for annotation)

import os
import sentence
from utils.path import open_input_file, open_output_file


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
        return ""
    else:
        symbol = value.strip(" ").replace(" ", "_")
        feature = name + value_separator + symbol
        return feature
    

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
    unlabeled_out = u"\t".join([uid, doc.year, chunk.phrase.lower(), hsent + '\n'])
    s_output_phr_occ.write(unlabeled_out)


def add_line_to_phr_feats(metadata_list, mallet_feature_list, s_output_phr_feats):
    """Create a tab separated string of features to be written out to phr_feats. The full
     line includes metadata followed by features."""
    # meta data to go at beginning of phr_feats output lines
    metadata_list.extend(mallet_feature_list)
    full_list = metadata_list
    mallet_feature_string = u"\t".join(full_list) + '\n'
    s_output_phr_feats.write(mallet_feature_string)


# returns (lowercased) nouns in a tag_string
def lc_nouns(tag_string):
    l_lc_nouns = []
    for tagged_token in tag_string.split(" "):
        (tok, tag) = tagged_token.rsplit("_", 1)
        if tag[0:1] == "N":
            l_lc_nouns.append(tok.lower())
    return l_lc_nouns
