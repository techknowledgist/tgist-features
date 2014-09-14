# sentence.py
# PGA 10/17/2012
# Classes and functions for language specific sentence chunking and feature creation.
# Utilized by tag2chunk.py 

# PGA 12/20/12 fixed bug in prev_n that caused ^ to be output as separate feature (because of ws separator)

#
### Notes to coders
# For each language: 
#    1. Add language key to language_list global variable
#    2. Create a Sentence subclass for the language (called Sentence_<language>) and populate its
#           feature_methods (using the @feature_method decorator)
#           (located below in file section labeled: "language specific Sentence subclass definitions")
#           Each feature method must be preceded by the decorator line (@feature_method).  It must take
#           two args (self, index) where index is the start location of the chunk within a sentence.
#           It must return the value of fname(<name>, <value>), as for example:
#           return(fname("prev_N", res))
#           By convention, <name> is identical to the name of the feature method and should be short but
#           descriptive.
#
#    3. Add an entry to d_sent_for_lang dictionary to map language key to Sentence subclass
#           (located below in file section labeled: "map languages to their sentence classes")
#    4. Add the chunk schema for the language to the chunk_schema function, keyed by the language key.
#           Note: For some languages (e.g., Chinese), an external file may be needed to allow the chunk schema
#           to be loaded with proper encoding of characters.   Name this file chunk_schema_<lang>.txt
#    5. Create a test function in tag2chunk.py that processes a sample file in the given lanuage.

import collections
import os
import codecs
from xml.sax.saxutils import escape

import config

# list of languages used to build dictionary of chunk schemas.
# NOTE: If a new language chunk schema is added, it must be added to this list.
language_list = ["en", "de", "cn"]

# map from lang to Sentence class for that language
# The entries for this dictionary are specified at the end of this file.
# There should be one entry per language handled by the Sentence class and subclasses.
d_sent_for_lang = {}

# Store chunk schemas in dict keyed by language
d_chunkSchema = {}


# creates a mallet feature name from a name and a value.
# If value is "", it returns None
# This is used by the sentence feature_methods.
def fname(name, value):
    if type(value) == int:
        value = str(value)
    if value == "":
        return(None)
    else:
        feature_name = name + "=" + value
        return(feature_name)

# Decorator implementation
# use feature_method decorator to mark methods to allow the 
# automated construction of a feature_method list from generic Sentence class
# and subclasses for each language.  In this way, we can easily encapsulate 
# feature functions for each language within the respective Sentence subclasses. 

def feature_method(method):
    # predicate indicating if the method is to be considered a feature method
    method.feature_p = True
    return method

# metaclass
class SentenceClass(type):
    # these are the standard parameters for a metaclass.
    # namespace is a dictionary of the attributes and methods of the class
    def __new__(metaclass, name, bases, namespace):
        cls = super(SentenceClass, metaclass).__new__(metaclass, name,
                                                      bases, namespace)
        cls.feature_methods = []
        # create the feature methods list once at class compile time
        for base in bases:
            if hasattr(base, "feature_methods"):
                cls.feature_methods.extend(base.feature_methods)
        # for every callable method in the namespace, test that feature_p is True
        # if so, add the method to the list of feature_methods for the class.
        for method in filter(callable, namespace.values()):
            if hasattr(method, "feature_p") and method.feature_p:
                cls.feature_methods.append(method)
        return cls

class Sentence(object):
    __metaclass__ = SentenceClass

    # given a tag_string, generate all chunks in the sentence in a chart
    # data structure
    # e.g. 'John_NNP went_VBD today_NN ._.'
    def __init__(self, sid, field, num, tag_string, chunk_schema):
        self.debug_p = False
        #self.debug_p = True
        # make sure there are no ws on edges since we will split on ws later
        self.tag_string = tag_string.strip(" ")
        self.len = 0
        self.last = 0
        self.sentence = ""
        self.toks = []
        self.tags = []
        # list of chunk instances within sent
        self.chunks = []
        # sid is number of sentence within entire document
        self.sid = sid
        # name of field (section) in which the sentence occurs
        self.field = field
        # number of sentence within the field
        self.num = num

        # chart is a sequence of chunk instances, one for each token
        self.chart = []
        self.init_chart(tag_string)
        self.chunk_chart_tech(chunk_schema)


    # utility methods

    # combines a doc section (header) with either 0 (if chunk appears in first
    # sentence of section) or 1 is it appears later.
    def make_section_loc(self, section, sent_no_in_section):
        loc = ""
        if sent_no_in_section == 0:
            loc = "sent1"
        else:
            loc = "later"
        section_loc = section + "_" + loc
        return(section_loc)

    # create initial chart using raw token list
    def init_chart(self, tag_string):
        if self.debug_p:
            print "[init_chart]tag_string: %s" % tag_string
        self.tags = tag_string.split(" ")
        self.len = len(self.tags)
        self.last = self.len - 1
        l_tok = []
        index = 0
        next = 1
        for tag in self.tags:
            # use rsplit with maxsplit = 1 so that we don't further split tokens like CRF07_BC
            (tok, tag) = tag.rsplit("_", 1)
            chunk = Chunk(index, next, tok, tag)
            self.chart.append(chunk)
            l_tok.append(tok)
            index += 1
            next += 1
        # create the sentence
        self.sentence = " ".join(l_tok)
        self.toks = l_tok

    # fill out phrasal chunks in the chart that match the technology phrase patterns.
    # This uses the patterns in the chunk_schema to combine tokens into a chunk
    # The chunk must end in certain toks, so we keep track of the last legal end token
    # and if it differs from the actual end token (such as a conjunction or adjective),
    # we create the chunk up to the last legal end token.
    def chunk_chart_tech(self, chunk_schema):

        # True when we are inside of a chunk
        # used to know if we should continue chunking based on
        # start chunk constraints or continue chunk constraints.
        inChunk_p = False

        #print "[Sent chunk]%s" % self.chart
        # last tag
        last_tag = " "

        # start index of current chunk
        cstart = 0

        # index of the last legal end token for a chunk
        last_legal_end_index = -1
        last_legal_phrase = ""
        # list of tags in a chunk
        last_legal_tag_sig = ""

        if self.debug_p:
            print "[chunk_chart]self.len: %i" % self.len
        for i in range(self.len):
            if self.debug_p:
                print "[chunk_chart]i: %i" % i

            chunk = self.chart[i]
            # check if chunk has same tag group as previous token
            if self.chunkable_p(chunk, inChunk_p, chunk_schema):
                # If this token starts a chunk, advance cstart to this token.
                # Otherwise cstart should already be the index of the first token in this chunk.
                if not inChunk_p:
                    cstart = i
                # extend the start chunk by concatenating the current token to the 
                # chunk token stored at the start index of the chunk.
                self.chart[cstart].chunk_end = i + 1

                if self.debug_p:
                    print "[chunk_chart]chunk phrase: |%s|, start: %i" % (self.chart[cstart].phrase, cstart)
                if not inChunk_p:
                    # set the label for the first element in the chunk to "tech"
                    self.chart[cstart].label = "tech"
                    # start the phrase using the current token
                    #self.chart[cstart].phrase = self.chart[cstart].phrase + " " + chunk.tok
                    self.chart[cstart].phrase = chunk.tok
                else:
                    # continue the phrase by concatenation
                    self.chart[cstart].phrase = self.chart[cstart].phrase + " " + chunk.tok

                self.chart[cstart].tag_sig = self.chart[cstart].tag_sig + "_" + chunk.tag
                #print "[chunk_chart_tech]appending chunk tag: %s" % chunk.tag
                self.chart[cstart].tokens.append(chunk.tok)
                self.chart[cstart].lc_tokens.append(chunk.tok.lower())
                inChunk_p = True
                # check if this token could be a legal end
                # ///PGA bug - sometimes the tag_sig includes the tags beyond the legal end
                if self.legal_end_p(chunk, chunk_schema):
                    last_legal_end_index = i
                    # update the last legal phrase and chunk tag list to the current token.
                    if self.debug_p:
                        print "[chunk_chart]last legal phrase so far: %s" % self.chart[cstart].phrase
                    last_legal_phrase = self.chart[cstart].phrase
                    last_legal_tag_sig = self.chart[cstart].tag_sig
            else:
                # terminate chunk
                # make sure the phrase and index correspond to the last legal end
                # We'll throw away any tokens up to the last legal ending of a chunk.
                if last_legal_end_index > -1:
                    self.chart[cstart].phrase = last_legal_phrase
                    if self.debug_p:
                        print "[chunk_chart]****Added |%s| at cstart |%i|" % (last_legal_phrase, cstart)
                    self.chart[cstart].tag_sig = last_legal_tag_sig[1:]
                    # also keep the list of tags as a list
                    # Note that we used the string tag_sig to build the tag list here since
                    # it makes it easy to back up to last_legal tag_sig.  Using lists is
                    # trickier, since append is destructive, making it harder to keep a last legal back up
                    # list, without contantly recopying the list.
                    self.chart[cstart].chunk_tags = self.chart[cstart].tag_sig.split("_")
                    self.chart[cstart].chunk_end = last_legal_end_index + 1
                else:
                    if self.debug_p:
                        print "[chunk_chart]****Rejected chunk" 

                    # reset the start chunk to remove all (now invalidated) phrasal info
                    self.chart[cstart].label = ""
                    #/// PGA fixed end of non-tech chunk to be tok_end
                    #self.chart[cstart].chunk_end = self.chart[cstart].tok_end + 1
                    self.chart[cstart].chunk_end = self.chart[cstart].tok_end
                    self.chart[cstart].phrase = self.chart[cstart].tok
                    self.chart[cstart].tag_sig = ""

                # last_legal_tag_sig tracks the last set of terms that 
                # includes a legitimate end term.  We use this if we reach the end of a chunk
                # at an illegal termination token and need to back up.
                last_legal_tag_sig = ""

                last_legal_end_index = -1
                cstart = i
                inChunk_p = False

    def legal_end_p(self, chunk, chunk_schema):
        # return True if this token can legally end a chunk
        try:
            if self.debug_p:
                print "[legal_end_p]in chunk, tok: %s" % chunk.tok
            pat = chunk_schema.d_end[chunk.tag]
            
            # check constraints
            if self.debug_p:
                print "[legal_end_p]pat: %s, tag: %s" % (pat, chunk.tag)
            test_val = False
            if pat != []:
                if pat[0] == "-" and chunk.tok.lower() not in pat[1:]:
                    test_val == True
                else:
                    test_val == False
                if self.debug_p:
                    print "[legal_end_p](pat[0] == - and chunk.tok.lower() not in pat[1:]): %r" % (test_val)
            if (pat == []) or (pat[0] == "n" and chunk_schema.noise_p(pat[1], chunk.tok.lower()) == False) or (pat[0] == "-" and chunk.tok.lower() not in pat[1:]) or (pat[0] == "+" and chunk.tok.lower() in pat[1:]):
                if self.debug_p:
                    print "[legal_end_p] matched!"
                return True
            else:
                return False
        except KeyError:
            return False
        
    # returns True if the current token/tag is part of a chunk according to
    # the patterns stored in chunk_schema and the current state (either in a
    # chunk or not).
    def chunkable_p(self, chunk, inChunk_p, chunk_schema):
        # match the chunk pattern depending on whether starting or
        # continuing a chunk
        # If the tag is not in our pattern, then return false
        self.debug_p = False
        #self.debug_p = True
        try:
            if inChunk_p:
                if self.debug_p:
                    print "[chunkable]in chunk, tok: %s" % chunk.tok
                pat = chunk_schema.d_cont[chunk.tag]
            else:
                if self.debug_p:
                    print "[chunkable]NOT yet in chunk, tok: %s" % chunk.tok
                pat = chunk_schema.d_start[chunk.tag]

            # check constraints
            if self.debug_p:
                print "[chunkable_p]pat: %s, inChunk_p: %s, tag: %s" % (pat, inChunk_p, chunk.tag)
            test_val = False
            if pat != []:

                if self.debug_p:
                    if (pat[0] == "n"):
                        print "[chunkable_p]pat[0] == 'n', term: %s, value: %s" % (chunk.tok.lower(), chunk_schema.noise_p(pat[1], chunk.tok.lower()))

                if pat[0] == "-" and chunk.tok.lower() not in pat[1:]:
                    test_val == True
                else:
                    test_val == False
                if self.debug_p:
                    print "[chunkable_p](pat[0] == - and chunk.tok.lower() not in pat[1:]): %r" % (test_val)
            # added noise_p constraint ("n") PGA
            if (pat == []) or (pat[0] == "n" and chunk_schema.noise_p(pat[1], chunk.tok.lower()) == False) or (pat[0] == "-" and chunk.tok.lower() not in pat[1:]) or (pat[0] == "+" and chunk.tok.lower() in pat[1:]):
                if self.debug_p:
                    print "[chunkable_p] matched!"
                return True
            else:
                return False
        except KeyError:
            return False

    def __display__(self):
        print "[Sent] %s" % self.tag_string
        for chunk in self.chart:
            chunk.__display__()

    # return sentence with np tag around the chunk starting at index
    def highlight_chunk(self, index):
        l_tok = self.toks
        last_tok = self.chart[index].chunk_end - 1
        l_highlight = []
        i = 0
        for tok in l_tok:
            if i == index:
                l_highlight.append("<np>")
            l_highlight.append(escape(tok))
            #l_highlight.append(tok)
            if i == last_tok:
                l_highlight.append("</np>")
            i += 1

        hsent = " ".join(l_highlight)
        return(hsent)
    
    def chunk_iter(self):
        chunk = self.chart[0]
        while True:
            if self.debug_p:
                chunk.__display__()
            yield(chunk)
            if chunk.chunk_end < self.len:
                if self.debug_p:
                    print "[chunk_iter]chunk_end: %i" % chunk.chunk_end
                chunk = self.chart[chunk.chunk_end]
            else:
                if self.debug_p:
                    print "[chunk_iter before break]chunk_end: %i" % chunk.chunk_end
                break


    # find index of the first prep in the chunk
    # Used to identify location of a PP
    # returns -1 if no prep
    def first_prep_idx(self, index):
        i = index
        chunk_end_loc = self.chart[index].chunk_end
        while i < chunk_end_loc:
            if self.chart[i].tag == "IN":
                return(i)
            i += 1
        return(-1)

    # returns the string of up to count tokens prior to index                                                                                         
    # if no tokens exist, it includes "^"                                                                                                             
    def prev_n(self, index, count, sep="_"):
        prev_n_string = ""
        start = index - count

        i = start
        while i < index:
            if i < 0:
                prev_n_string = prev_n_string + sep + "^"
            else:
                prev_n_string = prev_n_string + sep + self.chart[i].tok
            i += 1
        return(prev_n_string.lower()[1:])


    def next_n(self, index, count, sep="_"):
        ##print "[next_n]tag_string: %s" % self.tag_string
        next_n_string = ""
        end = self.chart[index].chunk_end + count
        sent_end = self.len - 1
        ##print "\n\n[next_n]chunk_end: %i, end: %i, sent_end: %i" % (self.chart[index].chunk_end, end, sent_end)
        ##print "[next_n]self.len: %i, tag_string: |%s|" % (self.len, self.tag_string)
        ##print "[next_n]current_chunk: %s" % self.chart[index].phrase
        # start just after chunk ends
        i = self.chart[index].chunk_end
        while i < end:
            if i > sent_end:
                next_n_string = next_n_string + sep + "^"
            else:
                next_n_string = next_n_string + sep + self.chart[i].tok
            i += 1
        return(next_n_string.lower()[1:])

    def next_n_tags(self, index, count, sep="_"):
        next_n_string = ""
        end = (self.chart[index].chunk_end + count) - 1
        sent_end = self.len - 1
        if sent_end < end:
            end = sent_end
        # start just after chunk ends
        i = self.chart[index].chunk_end
        while i <= end:
            next_n_string = next_n_string + sep + self.chart[i].tag
            i += 1
        return(next_n_string[1:])

    # The following are generic feature methods that are language independent

    @feature_method
    def document_loc(self, index):
        # PGA removed the "sent" prefix from the value 8/12/13
        res = "%d" % (self.sid)
        return fname("doc_loc", res)

    @feature_method
    def sentence_loc(self, index):
        chunk = self.chart[index]
        res = "%d-%d" % (chunk.chunk_start, chunk.chunk_end)
        return fname("sent_loc", res)

    @feature_method
    def section_loc(self, index):
        res = self.make_section_loc(self.field, self.num)
        return(fname("section_loc", res))

    
    # 12/29/13 PGA replaced prev_n3 and prev_n2 with prev_V and prev_Npr, prev_Jpr
    # These are no longer needed for English.
    # TODO: replace the next_ features in a similar way.

    # returns the string of up to count tokens prior to index
    # if no tokens exist, it includes "^"
    @feature_method
    def prev_n3(self, index):
        res = self.prev_n(index, 3)
        return(fname("prev_n3", res))

    @feature_method
    def prev_n2(self, index):
        res = self.prev_n(index, 2)
        return(fname("prev_n2", res))


    # returns the string of up to count tokens following the indexed chunk
    # if no tokens exist, it includes "^"
    @feature_method
    def next_n3(self, index):
        res = self.next_n(index, 3)
        return(fname("next_n3", res))

    @feature_method
    def next_n2(self, index):
        res = self.next_n(index, 2)
        return(fname("next_n2", res))

    @feature_method
    def next2_tags(self, index):
        res = self.next_n_tags(index, 2)
        return(fname("next2_tags", res))

    @feature_method
    def last_word(self, index):
        last_index = self.chart[index].chunk_end - 1
        res = self.chart[last_index].lc_tok
        return(fname("last_word", res))

    # suffix n-grams (3-5)

    @feature_method
    def suffix3(self, index):
        last_index = self.chart[index].chunk_end - 1
        last_word = self.chart[last_index].lc_tok
        #print "3 last word: %s" % last_word
        res = ""
        if len(last_word) >= 6:
            res = last_word[-3:]
        return(fname("suffix3", res))

    @feature_method
    def suffix4(self, index):
        last_index = self.chart[index].chunk_end - 1
        last_word = self.chart[last_index].lc_tok
        #print "5 last word: %s" % last_word
        res = ""
        if len(last_word) >= 7:
            res = last_word[-4:]
        return(fname("suffix4", res))

    @feature_method
    def suffix5(self, index):
        last_index = self.chart[index].chunk_end - 1
        last_word = self.chart[last_index].lc_tok
        res = ""
        if len(last_word) >= 8:
            res = last_word[-5:]
        return(fname("suffix5", res))

    @feature_method
    def first_word(self, index):
        last_index = self.chart[index].chunk_end - 1
        res = ""
        if index != last_index:
            res = self.chart[index].lc_tok
        # note, returns "" if length of phrase is 1
        return(fname("first_word", res))

    # length of the phrase
    @feature_method
    def plen(self, index):
        chunk = self.chart[index]
        chunk_len = chunk.chunk_end - chunk.chunk_start
        res = str(chunk_len)
        return(fname("plen", res))

    @feature_method
    # tag signature (sequence of tags as a string)
    def tag_list(self, index):
        res = self.chart[index].tag_sig
        # PGA /// hack to fix bug wherein some tag_sigs start with _
        # e.g. _JJ_NNS
        # This should be fixed at the source
        if res[0] == "_":
            res = res[1:]
        return(fname("tag_sig", res))

    

### language specific Sentence subclass definitions

class Sentence_english(Sentence):

    #print "Creating Sentence_english subclass"


    # prev_V (originally called prev_V2 to distinguish from prev_V, now renamed to prev_Vstrong and commented out)
    # a less restrictive feature looking for a preceding verb
    # deals with cases like:
    # Cache memory control circuit including summarized cache tag memory summarizing cache tag information in parallel processor system
    # in the above, we don't want "summarized" to be treated as preceding verb for NP memory.
    # A multi-processor system includes a plurality of processor node control circuits in respective processor nodes , and a <np> cache memory </np> which is an external cache .
    # in the above, we don't want "plurality" to block finding "includes" for the NP circuits.
    # however, the verb in this case will include the prep "of" if that is the last prep encountered.  ie. prev_V2=includes_of
    # This is a nice feature to detect cases of N1 of N2 but won't work if the verb includes a particle of its own.
    # fixed PGA 12/29/13

    # TODO Extend this to handle the case of chunks within a list (to capture all
    # items in the scope of "contains" or "includes").
    # We want to capture the verb to left of the list for all members of the list, 
    # not just the first.  Also may need to adjust for prev_n and prev_prep

    # example
    # thus_RB giving_VBG a_DT relatively_RB high_JJ ranking_NN to_TO musical_JJ 
    # selections_NNS categorized_VBN as_IN ``_`` cool_JJ jazz_NN ._. ''_''

    # in the previous case, the previous verb to "cool jazz" should be "categorized_as"

    # the list includes categorized recordings
    # here "recordings" is modified by the verb categorized but direct object of "includes
    
    # To handle such cases, we look at the word preceding a past tense verb to see if it
    # is an aux.  In this cases, we assume the past verb is the actual dominating verb
    # rather than a modifier.
    # if preceded by a noun, we consider it a dominating modifier and also make it the preceding verb.

    # We also try to capture cases such as
    # refers to X as Y => refers_to_as for Y
    # But we disallow too many intermediate nouns, as in
    # sends media to users over the internet
    # BUG: we allow adj between verb and prep causing
    # includes next to each mac address => includes_to
    # being limitative to => being_to

    @feature_method
    def prev_V(self, index):
        verb = ""
        prep = ""
        prep2 = ""
        past_verb = ""
        verb_prep = ""
        noun_found_p = False
        i = index -1
        while i > 0:
            # terminate if verb is found
            # but not if the verb is past participle (VBN) or past tense (VBD)
            # which could be an adjectival use of the verb.
            # Also look for a form of "to be" before a VBN or VBD
            # and accept the verb if an aux is found.
            if self.chart[i].tag in ["VBG", "VBP", "VBZ", "VB"]:
                verb = self.chart[i].lc_tok
                break

            # A past tense verb is ambiguous, could me main verb or a modifier
            # He returned the reviewed book  vs.
            # He reviewed the book
            # It does not handle correctly:
            # invention is providing selected files ...
            # impose execution of Y
            # describe a plurality of Y
            if self.chart[i].tag in ["VBD", "VBN"]:
                # if preceded by a determiner, treat it as a modifier rather than the dominant verb
                if i > 0 and ((self.chart[i-1].tag == "DT") or (self.chart[i-1].tag[0] == "V" and (self.chart[i-1].lc_tok not in ["be", "been", "being", "is", "am", "are", "was", "were", "have", "had", "has", "having"]))):
                    past_verb = self.chart[i].lc_tok
                else:
                    # treat the past tense verb as the main verb
                    verb = self.chart[i].lc_tok
                    break

            """
            # Do not terminate if a noun is reached before a verb
            # But do terminate if a second noun is reached before a verb
            if self.chart[i].tag[0] == "N":
                if noun_found_p:
                    break
                else:
                    noun_found_p = True
            """
            # It is more conservative to break if a noun is encountered.
            if self.chart[i].tag[0] == "N":
                break

            # if we hit an adj after a prep, don't create a prev_V feature
            if prep != "" and self.chart[i].tag[0] == "J":
                break

            # keep a prep if reached before verb
            # this could be a particle.  Note we always replace 
            # any previously encountered prep, giving us the one
            # closest to the verb, assuming we find a verb.
            # 12/29/13 PGA added "TO"
            # retained a second prep if there is one in prep2
            # This allows us to capture previous verbs with multiple preps
            # x refers to a plurality of y => refers_to_of
            # referred to as y => referred_to_as
            if self.chart[i].tag in ["RP", "IN", "TO"]:
                if prep != "":
                    # save the prep to the right of the current prep
                    prep2 = prep
                # capture the new prep (which should be closer to the verb to the left)
                prep = self.chart[i].lc_tok


            # if a comma is found after a prep, we should stop looking for a dominating verb.
            # example: 
            # an_DT online_JJ system_NN provides_VBZ selected_VBN media_NNS files_NNS ,_, chosen_VBN from_IN among_IN a_DT plurality_NN of_IN media_NNS files_NNS ,_, to_TO a_DT user_NN over_IN a_DT packet-switched_JJ network_NN ._.
            # We don't want "chosen_from_among" to be the prev_V for "user".
                
            if self.chart[i].lc_tok == "," and prep != "":
                break

            # keep looking 
            i = i - 1
        if verb != "":
            # 11/9/21 PGA replaced blank with _
            # 12/29/13 PGA added prep2
            if prep != "":
                verb_prep = verb + "_" + prep
                if prep2 != "":
                    verb_prep = verb_prep + "_" + prep2
            else:
                verb_prep = verb
            #print "[sentence.py] verb_prep: %s" % verb_prep
        res = verb_prep
        return(fname("prev_V", res))        

    # prev_VNP combines prev_Npr and prev_V in order to capture larger
    # syntactic units of the form: increase the speed of the computer
    @feature_method
    def prev_VNP(self, index):

        res = ""
        noun = ""
        prep = ""
        noun_prep = ""
        i = index - 1
        distance_limit = 4
        #print "[prev_Npr]Starting"
        while i > 0 and distance_limit > 0:
            # PGA: It may make sense to add some blocking conditions,
            # such as punc or verb.
            if self.chart[i].tag in ["RP", "IN", "TO"]:
                prep = self.chart[i].lc_tok

            elif prep != "" and self.chart[i].tag[0] == "N":
                noun = self.chart[i].lc_tok
                #print "[prev_Npr]noun: %s" % noun
                break
            # adj and det could be part of the current NP, so ignore those
            # but avoid: person skilled in => person_in
            elif prep == "" and self.chart[i].tag[0] in ["J", "D"] :
                # keep looking 
                pass
            else:
                # give up
                break
            i = i - 1
            distance_limit = distance_limit - 1
        #print "[prev_Npr]distance_limit: %i" % distance_limit
        if noun != "" and prep != "":
            noun_prep = noun + "|" + prep
            #print "[prev_VNP]noun_prep: %s" % noun_prep
            
            # if we have found a noun_prep, continue looking left for a preceeding
            # verb
            verb = ""
            prep = ""
            prep2 = ""
            past_verb = ""
            verb_prep = ""
            noun_found_p = False
            # use j as index for our inner loop
            j = i - 1
            while j > 0:
                #print "[prev_VNP] loop j = %i" % j
                # terminate if verb is found
                # but not if the verb is past participle (VBN) or past tense (VBD)
                # which could be an adjectival use of the verb.
                # Also look for a form of "to be" before a VBN or VBD
                # and accept the verb if an aux is found.
                if self.chart[j].tag in ["VBG", "VBP", "VBZ", "VB"]:
                    verb = self.chart[j].lc_tok
                    break

                # A past tense verb is ambiguous, could me main verb or a modifier
                # He returned the reviewed book  vs.
                # He reviewed the book
                # It does not handle correctly:
                # invention is providing selected files ...
                # impose execution of Y
                # describe a plurality of Y
                if self.chart[j].tag in ["VBD", "VBN"]:
                    # if preceded by a determiner, treat it as a modifier rather than the dominant verb
                    if j > 0 and ((self.chart[j-1].tag == "DT") or (self.chart[j-1].tag[0] == "V" and (self.chart[j-1].lc_tok not in ["be", "been", "being", "is", "am", "are", "was", "were", "have", "had", "has", "having"]))):
                        past_verb = self.chart[j].lc_tok
                    else:
                        # treat the past tense verb as the main verb
                        verb = self.chart[j].lc_tok
                        break

                # Fail if a noun is encountered before a verb.
                if self.chart[j].tag[0] == "N":
                    break

                # if we hit an adj after a prep, don't create a prev_V feature
                if prep != "" and self.chart[j].tag[0] == "J":
                    break


                # keep a prep if reached before verb
                # this could be a particle.  Note we always replace 
                # any previously encountered prep, giving us the one
                # closest to the verb, assuming we find a verb.
                # 12/29/13 PGA added "TO"
                # retained a second prep if there is one in prep2
                # This allows us to capture previous verbs with multiple preps
                # x refers to a plurality of y => refers_to_of
                # referred to as y => referred_to_as
                if self.chart[j].tag in ["RP", "IN", "TO"]:
                    if prep != "":
                        # save the prep to the right of the current prep
                        prep2 = prep
                    # capture the new prep (which should be closer to the verb to the left)
                    prep = self.chart[j].lc_tok
                    #print "[prev_VNP]found prep: %s" % prep

                # if a comma is found after a prep, we should stop looking for a dominating verb.
                # example: 
                # an_DT online_JJ system_NN provides_VBZ selected_VBN media_NNS files_NNS ,_, chosen_VBN from_IN among_IN a_DT plurality_NN of_IN media_NNS files_NNS ,_, to_TO a_DT user_NN over_IN a_DT packet-switched_JJ network_NN ._.
                # We don't want "chosen_from_among" to be the prev_V for "user".

                if self.chart[j].lc_tok == "," and prep != "":
                    break

                # keep looking 
                #print "[prev_VNP]keep looking..."
                j = j - 1
            if verb != "":
                # 11/9/21 PGA replaced blank with _
                # 12/29/13 PGA added prep2
                if prep != "":
                    verb_prep = verb + "_" + prep
                    if prep2 != "":
                        verb_prep = verb_prep + "_" + prep2
                else:
                    verb_prep = verb
                #print "[prev_VNP] verb_prep: %s" % verb_prep
            if verb_prep != "":
                # create a feature including the verb and noun_prep
                res = verb_prep + "|" + noun_prep
                #print "[prev_VNP]res: %s" % res
            return(fname("prev_VNP", res))        

    # first noun_prep to the left of chunk, within 4 words
    # 12/29/13 PGA changed prev_N to prev_Npr to capture cases of NOUN PREP
    @feature_method
    def prev_Npr(self, index):
        noun = ""
        prep = ""
        noun_prep = ""
        i = index - 1
        distance_limit = 4
        #print "[prev_Npr]Starting"
        while i > 0 and distance_limit > 0:
            # PGA: It may make sense to add some blocking conditions,
            # such as punc or verb.
            if self.chart[i].tag in ["RP", "IN", "TO"]:
                prep = self.chart[i].lc_tok

            elif prep != "" and self.chart[i].tag[0] == "N":
                noun = self.chart[i].lc_tok
                #print "[prev_Npr]noun: %s" % noun
                break
            # adj and det could be part of the current NP, so ignore those
            # but avoid: person skilled in => person_in
            elif prep == "" and self.chart[i].tag[0] in ["J", "D"] :
                # keep looking 
                pass
            else:
                # give up
                break
            i = i - 1
            distance_limit = distance_limit - 1
        #print "[prev_Npr]distance_limit: %i" % distance_limit
        if noun != "" and prep != "":
            noun_prep = noun + "_" + prep
            #print "[prev_Npr]noun_prep: %s" % noun_prep
        res = noun_prep
        return(fname("prev_Npr", res))


    # first adj_prep to the left of chunk, within 4 words
    # 12/29/13 PGA 



    @feature_method
    def prev_Jpr(self, index):
        adj = ""
        prep = ""
        adj_prep = ""
        i = index - 1
        distance_limit = 4
        #print "[prev_Jpr]Starting"
        while i > 0 and distance_limit > 0:
            # PGA: It may make sense to add some blocking conditions,
            # such as punc or verb.
            if self.chart[i].tag in ["RP", "IN", "TO"]:
                prep = self.chart[i].lc_tok

            elif prep != "" and self.chart[i].tag[0] == "J":
                adj = self.chart[i].lc_tok
                #print "[prev_Jpr]adj: %s" % adj
                break
            # adj and det could be part of the current NP, so ignore those
            # until we have seen a prep
            elif self.chart[i].tag[0] in ["J", "D"] :
                # keep looking 
                pass
            else:
                # give up
                break
            i = i - 1
            distance_limit = distance_limit - 1
        #print "[prev_Jpr]distance_limit: %i" % distance_limit
        if adj != "" and prep != "":
            adj_prep = adj + "_" + prep
            #print "[prev_Jpr]adj_prep: %s" % adj_prep
        res = adj_prep
        return(fname("prev_Jpr", res))

    # Adj must be immediately bfore index term
    @feature_method
    def prev_J(self, index):
        res = ""
        if index >= 1:
            i = index - 1
            if self.chart[i].tag[0] == "J":
                res = self.chart[i].lc_tok
        return(fname("prev_J", res))


class Sentence_german(Sentence):
    """Class that contains the German feature methods. These feature methods are often
    very similar to the English ones. You could almost imagine having some non feature
    methods on the parent class that implements comon behaviour."""
    
    #print "Creating Sentence_german subclass"

    # previous verb
    # return closest verb to left of NP
    # as well as prep or particle if there is one after verb
    @feature_method
    def prev_V(self, index):
        verb = ""
        i = index -1
        while i > 0:
            # terminate if verb is found, but skip copula
            if self.chart[i].tag[0] == "V" and self.chart[i].tag != 'VAINF':
                verb = self.chart[i].lc_tok
                break
            # terminate if a noun is reached before a verb
            if self.chart[i].tag[0] == "N":
                break
            # keep looking 
            i = i - 1
        return(fname("prev_V", verb.lower()))
    
    # first noun to the left of chunk, within 3 words
    # NOTE MV: same as for English
    @feature_method
    def prev_N(self, index):
        noun = ""
        i = index - 1
        distance_limit = 3
        while i > 0 and distance_limit > 0:
            # terminate if verb is found
            if self.chart[i].tag[0] == "N":
                noun = self.chart[i].lc_tok
                break
            else:
                # keep looking 
                i = i - 1
            distance_limit = distance_limit - 1
        res = noun.lower()
        return(fname("prev_N", res))


    # initial adj in chunk, if there is one
    @feature_method
    def chunk_lead_J(self, index):
        res = ""
        if self.chart[index].tag == "ADJA":
            res = self.chart[index].lc_tok
        return(fname("chunk_lead_J", res))

    # initial V-ing verb in chunk, if there is one
    # NOTE MV: not much going on in German here, by skipping the copula you usually
    # already have what you want
    #@feature_method
    #def chunk_lead_VBG(self, index):
    #    res = ""
    #    if self.chart[index].tag[0] == "VBG":
    #        res = self.chart[index].lc_tok
    #    return(fname("chunk_lead_VBG", res))

    # head of prep in chunk, if there is one
    @feature_method
    def von_head(self, index):
        res = ""
        i = index
        head = ""
        prep_idx = self.first_prep_idx(index)
        if prep_idx != -1:
            head_loc = prep_idx - 1
            head = self.chart[head_loc].lc_tok
            res = head.lower()
        return(fname("von_head", res))

    # previous adj (JJ, JJR, JJS)
    # Adj must be immediately bfore index term
    @feature_method
    def prev_J(self, index):
        res = ""
        i = index - 1
        if self.chart[i].tag == "ADJA":
            res = self.chart[i].lc_tok
        return(fname("prev_J", res))

    # first adjective in the chunk
    @feature_method
    def initial_J(self, index):
        res = ""
        i = index
        if self.chart[i].tag == "ADJA":
            res = self.chart[i].lc_tok
        return(fname("initial_J", res))

    @feature_method
    def initial_V(self, index):
        res = ""
        i = index
        if self.chart[i].tag[0] == "V":
            res = self.chart[i].lc_tok
        return(fname("initial_V", res))

    # If a prep occurs directly after the chunk, return the token
    # NOTE MV: same as in English
    @feature_method
    def following_prep(self, index):
        res = ""
        i = index
        following_index = self.chart[i].chunk_end
        if following_index <= self.last:
            if self.chart[following_index].tag == "IN":
                res = self.chart[following_index].lc_tok
        return(fname("following_prep", res))

    # find index of the first prep in the chunk
    # Used to identify location of a PP
    # returns -1 if no prep
    # NOTE MV: this overrules the method on the super class, but the only change is in the
    # name of the tag so we can do this in a nocer way
    def first_prep_idx(self, index):
        i = index
        chunk_end_loc = self.chart[index].chunk_end
        while i < chunk_end_loc:
            if self.chart[i].tag == "APPR":
                return(i)
            i += 1
        return(-1)
    

class Sentence_chinese(Sentence):

    #print "Creating Sentence_chinese subclass"
    
    # We lower case tokens in Chinese because occasionally English words show up
    # in Chinese patents

    # first noun to the left of chunk, within 3 words
    @feature_method
    def prev_N(self, index):
        noun = ""
        i = index - 1
        distance_limit = 3
        while i > 0 and distance_limit > 0:
            # terminate if NN is found
            if self.chart[i].tag == "NN":
                noun = self.chart[i].lc_tok
                break
            else:
                # keep looking 
                i = i - 1
            distance_limit = distance_limit - 1
        return(fname("prev_N", noun))
    
    @feature_method
    def penultimate_word (self, index):
        last_index = self.chart[index].chunk_end - 1
        if last_index ==0:
            return(fname("last_word", ''))
        else:
            res = self.chart[last_index-1].lc_tok
            return(fname("last_word", res))
        
    @feature_method
    def prev_V(self, index):
        verb = ""
        i = index -1
        while i > 0:
            # terminate if verb is found
            if self.chart[i].tag[0] == "V":
                verb = self.chart[i].lc_tok
                break
            # terminate if a noun is reached before a verb
            if self.chart[i].tag[0] == "N":
                break
            """
            # keep a prep if reached before verb
            if self.chart[i].tag[0] in ["P", "IN"]:
                prep = self.chart[i].lc_tok
            else:
                # keep looking
            """
            i = i - 1
        """
        if verb != "":
            verb_prep = verb + "_" + prep
        res = verb_prep.lower()
        """
        return(fname("prev_V", verb))

    # first JJ or VA in the chunk
    @feature_method
    def first_Adj(self, index):
        res = ""
        i = index 
        while i < self.chart[index].chunk_end:
            if self.chart[i].tag == "JJ" or self.chart[i].tag == "VA":
                res = self.chart[i].lc_tok
                break
            i = i + 1
        return(fname("first_Adj", res))

    # Chunk-final JJ or VA
    @feature_method
    def final_Adj(self, index):
        res = ""
        i = self.chart[index].chunk_end - 1
        while i>=index:
            if self.chart[i].tag == "JJ" or self.chart[i].tag == "VA":
                res = self.chart[i].lc_tok
                break
            i = i - 1
        return(fname("prev_J", res))

    #previous (OD|CD)+M combination
    @feature_method
    def prev_CD_M(self, index):
        measure = ""
        i = index -1
        distance_limit = 3
        while i > 0 and distance_limit > 0:        
            # terminate if verb is found
            if self.chart[i].tag == "M":
                measure = self.chart[i].lc_tok
                if i > 1:
                    measure = measure + ' ' + self.chart[i-1].lc_tok
                break
            i = i - 1
        return(fname("prev_CD_M", measure))

    #previous DT within 3 words
    @feature_method
    def prev_DT(self, index):
        determiner = ''
        i = index -1
        distance_limit = 3
        while i > 0 and distance_limit > 0:        
            # terminate if verb is found
            if self.chart[i].tag == "DT":
                determiner = self.chart[i].lc_tok
                break
            i = i - 1
        return(fname("prev_DT", determiner))


### chunking

# chunking related classes
class Chunk:
    
    def __init__(self, tok_start, tok_end, tok, tag ):
        self.sid = -1  # sentence id (set in process_doc)
        self.tok_start = tok_start
        self.tok_end = tok_end
        self.tok = tok
        # normalize case since token will be used as a feature value for some features (e.g. chunk_lead_J)
        self.lc_tok = tok.lower()
        self.tag = tag
        # label is changed if a chunk pattern is matched
        self.label = tag
        # if not a multi-token chunk, chunk_start/end should be same as
        # tok_start/end
        self.chunk_start = tok_start
        self.chunk_end = tok_end
        self.head = ""
        self.of_head = ""
        self.phrase = ""
        # list of strings 
        self.tokens = []
        self.lc_tokens = []
        self.premods = []
        self.postmod = None  # connector + NOMP
        self.precontext = []
        self.postcontext = []
        # list of tags in a phrasal chunk
        self.chunk_tags = []
        # for head idx, -1 means no head found
        self.head_idx = -1
        self.prep_head_idx = -1
        self.chunk_lead_J = ""
        self.chunk_lead_VBG = ""
        # string of tags for words in the chunk, separated by _
        self.tag_sig = ""

    def __str__(self):
        return "<Chunk %d %d:%d '%s'>" % (self.sid, self.chunk_start, self.chunk_end, self.phrase)

    # return the token loc in sentence for head of the chunk
    def head_idx(self):
        idx = self.tok_start
        head_idx = idx
        l_tags = self.chunk_tags
        for tag in l_tags:
            # check for termination conditions
            if tag in ["IN", "DT", "CC"]:
                break
            else:
                head_idx = idx    
            idx += 1
        # for debugging, print the idx within the phrase, rather than within the sentence
        rel_idx = head_idx - self.tok_start
        #print "[head_idex]rel_idx: %i" % rel_idx
        return(idx)

    # return the index of the head of a prep phrase in the chunk, if there is one.  If not
    # return -1.
    def prep_head_idx(self):
        idx = self.tok_start
        head_idx = -1
        l_tags = self.chunk_tags
        prep_found_p = False
        nv_found_p = False
        for tag in l_tags:

            if prep_found_p == True:
                # check for termination conditions
                if tag in ["IN"]:
                    break
                else:
                    if tag[0] == "N" or tag[0] == "V":
                        head_idx = idx    
                        nv_found_p = True
            # is the tag a prep?
            if tag == "IN":
                prep_found_p = True
            idx += 1

        # for debugging, print the idx within the phrase, rather than within the sentence
        rel_idx = head_idx - self.tok_start
        #print "[prep_head_idx]rel_idx: %i" % rel_idx
        return(idx)
            

    def __display__(self):
        print "[Chunk]Chunk type: %s, phrase: %s, %i, %i" % (self.tag, self.phrase, self.chunk_start, self.chunk_end)



# instance of a chunk definition in the form of two dictionaries:
# conditions for matching the start of a chunk (tags + token constraints)
# conditions for continuing a chunk (tags + token constraints)
class chunkSchema:
    
    def __init__(self, start_pat, cont_pat, end_pat, noise_files=[]):
        self.d_start = {}
        self.d_cont = {}
        self.d_end = {}
        # store noise_word lists in a dictionary of dictionaries for use by chunker
        self.noise_files = noise_files
        self.d_noise = {}

        for pat in start_pat:
            key = pat[0]
            value = pat[1]
            self.d_start[key] = value
        for pat in cont_pat:
            key = pat[0]
            value = pat[1]
            self.d_cont[key] = value
        for pat in end_pat:
            key = pat[0]
            value = pat[1]
            self.d_end[key] = value

        for key, filename in noise_files:
            self.add_noise_list(key, filename)

    def add_noise_list(self, name, filename):
        # file should contain one term per line.
        # add a list of terms to be indexed under [name][term] as noisewords with value True
        filepath = os.path.join(config.ANNOTATION_DIRECTORY, filename)
        #print "[add_noise_list]Adding chunker noise list in %s" % filepath 
        s_noise = open(filepath)
        self.d_noise.setdefault(name, {})
        for term in s_noise:
            term = term.strip()
            self.d_noise[name].setdefault(term, True)
        s_noise.close()

    def noise_p(self, name, term):
        # return False if term is not in noise dict for name
        return self.d_noise[name].get(term, False)

# Chunk schema definitions
# constraints are indicated by 
# "-" none of the following strings
# "+" only the following strings
# "n" noise terms are in noise dictionary keyed by string after "n"
# [] no constraints
# end_pat are the legal POS that can end a chunk
#def chunk_schema_en():
def chunk_schema(lang):
    start_pat = []
    cont_pat = []
    end_pat = []
    noise_files = []
    # noise files should be in annotation_directory for now (../patent-classifier/ontology/annotation)


    # most restrictive schema omits verbs, "of", conjunctions, many adjectival modifiers (via "n" noise list)
    if lang == "en":
        both_pat =  [ ["NN", ["-", "fig", "figure"]], ["NNP", ["-", "fig", "figure"] ], ["NNS", []], ["NNPS", []], ["POS", []],  ["JJ", ["n", "noise_av"]] , ["JJR", ["-", "more"] ], ["JJS", ["-", "most"] ], ["FW", ["-", "e.g.", "i.e"] ]  ]
        #start_pat = [ ["NN", ["-", "method"]] ] 
        start_pat = []
        # 11/16/12 PGA removed "of" from cont_pattern, removed "CC"
        cont_pat = [ ["NN", []]  ]
        end_pat = [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []] ]
        start_pat.extend(both_pat)
        cont_pat.extend(both_pat)
        noise_files = [["noise_av", "en_jj_vb.noise"]]

    # no verbs but includes "of"
    if lang == "en_w_of":
        both_pat =  [ ["NN", ["-", "fig", "figure"]], ["NNP", ["-", "fig", "figure"] ], ["NNS", []], ["NNPS", []], ["POS", []],  ["JJ", ["n", "noise_av"]] , ["JJR", ["-", "more"] ], ["JJS", ["-", "most"] ], ["FW", ["-", "e.g.", "i.e"] ]  ]
        #start_pat = [ ["NN", ["-", "method"]] ] 
        start_pat = []
        # 11/16/12 PGA removed "of" from cont_pattern, removed "CC"
        cont_pat = [ ["NN", []], ["VBN", []], ["DT",  []], ["RP", []], ["IN", ["+", "of"]] ]
        end_pat = [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []] ]
        start_pat.extend(both_pat)
        cont_pat.extend(both_pat)
        noise_files = [["noise_av", "en_jj_vb.noise"]]

    if lang == "en_w_verbs":
        both_pat =  [ ["NN", ["-", "fig", "figure"]], ["NNP", ["-", "fig", "figure"] ], ["NNS", []], ["NNPS", []], ["POS", []],  ["JJ", ["n", "noise_av"]] , ["JJR", ["-", "more"] ], ["JJS", ["-", "most"] ], ["FW", ["-", "e.g.", "i.e"] ], ["VBG", ["n", "noise_av"]]  ]
        #start_pat = [ ["NN", ["-", "method"]] ] 
        start_pat = []
        # 11/16/12 PGA removed "of" from cont_pattern, removed "CC"
        cont_pat = [ ["NN", []], ["VBN", []], ["DT",  []], ["RP", []] ]
        end_pat = [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []], ["VBG", ["n", "noise_av"]  ] ]
        start_pat.extend(both_pat)
        cont_pat.extend(both_pat)
        noise_files = [["noise_av", "en_jj_vb.noise"]]

    if lang == "en_w_lists":
        both_pat =  [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []], ["POS", []],  ["JJ", ["-", "further", "such", "therebetween", "same", "following", "respective", "first", "second", "third", "fourth", "respective", "preceding", "predetermined", "next", "more"] ], ["JJR", ["-", "more"] ], ["JJS", ["-", "most"] ], ["FW", ["-", "e.g.", "i.e"] ], ["VBG", ["-", "describing", "improving", "using", "employing",  "according", "resulting", "having", "following", "including", "containing", "consisting", "disclosing"]  ] ] 
        #start_pat = [ ["NN", ["-", "method"]] ] 
        start_pat = []
        # 11/16/12 PGA removed "of" from cont_pattern, removed "CC"
        cont_pat = [ ["NN", []], ["VBN", []], ["DT",  []], ["RP", []] ]
        end_pat = [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []], ["VBG", ["-", "describing", "improving", "using", "employing", "according", "resulting", "having", "following", "including", "containing", "consisting", "disclosing", "pertaining", "being", "comprising", "corresponding"]  ] ]
        start_pat.extend(both_pat)
        cont_pat.extend(both_pat)

    # NOTE: this was the first set created, it was used for the T&E evaluation, it was
    # also used when we first created candidates for annotation
    if lang == "en_w_of_org":
        both_pat =  [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []], ["POS", []],  ["JJ", ["-", "further", "such", "therebetween", "same", "following", "respective", "first", "second", "third", "fourth", "respective", "preceding", "predetermined", "next", "more"] ], ["JJR", ["-", "more"] ], ["JJS", [] ], ["FW", ["-", "e.g.", "i.e"] ], ["VBG", ["-", "describing", "improving", "using", "employing",  "according", "resulting", "having", "following", "including", "containing", "consisting", "disclosing"]  ] ] 
        #start_pat = [ ["NN", ["-", "method"]] ] 
        start_pat = []
        cont_pat = [ ["NN", []], ["VBN", []], ["IN", ["+", "of"]], ["DT",  []], ["CC", []], ["RP", []] ]
        end_pat = [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []], ["VBG", ["-", "describing", "improving", "using", "employing", "according", "resulting", "having", "following", "including", "containing", "consisting", "disclosing", "pertaining", "being", "comprising", "corresponding"]  ] ]
        start_pat.extend(both_pat)
        cont_pat.extend(both_pat)

    elif lang == "de":
        start_pat =  [ ["NN", []], ["NE", []], ["ADJA", []] ]
        cont_pat = [ ["NN", []], ["NE", []], ["ADJA", []], ["APPR", ["+", "von"]], ["ART", ["+", "des", "der"]] ]
        end_pat = [ ["NN", []], ["NE", []] ]

    elif lang == "cn":
        # ///PGA - this should be set to True if an external chunk schema file exists
        # (needed for handling non-ascii chars)
        load_patterns = True
        #load_patterns = False
        if load_patterns:
            start_pat = []
            cont_pat = []
            end_pat = []
            # changed the path to the patterns so this works when called from a
            # script in this directory or a sister directory (ie, runtime)
            # TODO: needs a less hackish solution
            fh = codecs.open("../doc_processing/chunk_schema_%s.txt" % lang, encoding='utf-8')
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                add_chunk_pattern_element(line, start_pat, cont_pat, end_pat)
        else:
            start_pat =  [ ["NN", []], ["NR", []], ["NT", []], ["JJ", []], ["VA", []] ]
            cont_pat = [ ["NN", []], ["NR", []], ["NT", []], ["JJ", []], ["VA", []], ["DEG", []], ["DEC", []] ]
            end_pat = [ ["NN", []]  ]
    
    cs = chunkSchema(start_pat, cont_pat, end_pat, noise_files)
    return(cs)

# This is needed to deal with proper encoding of Chinese characters within chunk patterns
def add_chunk_pattern_element(line, start_pat, cont_pat, end_pat):
    (pattern_type, l_elements) = line.split("\t")
    l_elements = l_elements.split()
    tag = l_elements[0]
    constraint = l_elements[1:]
    if pattern_type == "start_pat":
        pattern_list = start_pat
    elif pattern_type == "cont_pat":
        pattern_list = cont_pat
    elif pattern_type == "end_pat":
        pattern_list = end_pat
    else:
        print "Warning: illegal pattern type"
        return
    pattern_list.append([tag, constraint])


# populate the d_chunkSchema with schemas for each language
for lang in language_list:
    d_chunkSchema[lang] = chunk_schema(lang)

# return a Sentence object for the given language and arguments
def get_sentence_for_lang(lang, sent_args):
    sentence_func = d_sent_for_lang.get(lang)
    # the * unwraps the list of args
    ###print "[get_Sentence_for_lang] sentence_func: %s, args: %s" % (sentence_func, sent_args)
    sent = sentence_func(*sent_args)
    return(sent)

### map languages to their sentence classes
d_sent_for_lang["en"] = Sentence_english
d_sent_for_lang["cn"] = Sentence_chinese
d_sent_for_lang["de"] = Sentence_german

"""
if __name__ == "__main__":
    e = Sentence_english("e1")
    for method in e.feature_methods:
        method(e) # unbound methods, so must supply instance
    print "sid: %s" % self.sid
"""

