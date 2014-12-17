# sentence.py
# PGA 10/17/2012
# Classes and functions for language specific sentence chunking and feature creation.
# Utilized by tag2chunk.py 
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

import codecs
from xml.sax.saxutils import escape

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

    # fill out phrasal chunks in the chart
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
        last_legal_chunk_tags = []

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
                    print "chunk phrase: |%s|, start: %i" % (self.chart[cstart].phrase, cstart)
                if not inChunk_p:
                    # set the label for the first element in the chunk to "tech"
                    self.chart[cstart].label = "tech"
                    # start the phrase using the current token
                    #self.chart[cstart].phrase = self.chart[cstart].phrase + " " + chunk.tok
                    self.chart[cstart].phrase = chunk.tok
                else:
                    # continue the phrase by concatenation
                    self.chart[cstart].phrase = self.chart[cstart].phrase + " " + chunk.tok

                self.chart[cstart].chunk_tags.append(chunk.tag)
                self.chart[cstart].tokens.append(chunk.tok)
                self.chart[cstart].lc_tokens.append(chunk.tok.lower())
                inChunk_p = True
                # check if this token could be a legal end
                if self.legal_end_p(chunk, chunk_schema):
                    last_legal_end_index = i
                    # update the last legal phrase
                    last_legal_phrase = self.chart[cstart].phrase
                    last_legal_chunk_tags = self.chart[cstart].chunk_tags
            else:
                # terminate chunk
                # make sure the phrase and index correspond to the last legal end
                # We'll throw away any tokens up to the last legal ending of a chunk.
                if last_legal_end_index > -1:
                    self.chart[cstart].phrase = last_legal_phrase
                    self.chart[cstart].chunk_tags = last_legal_chunk_tags
                    self.chart[cstart].chunk_end = last_legal_end_index + 1
                else:
                    # reset the start chunk to remove all (now invalidated) phrasal info
                    self.chart[cstart].label = ""
                    self.chart[cstart].chunk_end = self.chart[cstart].tok_end + 1
                    self.chart[cstart].phrase = self.chart[cstart].tok
                    self.chart[cstart].chunk_tags = []

                # last_legal_chunk_tags tracks the last set of terms that 
                # includes a legitimate end term.  We use this if we reach the end of a chunk
                # at an illegal termination token and need to back up.
                last_legal_chunk_tags = []

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
            if (pat == []) or (pat[0] == "-" and chunk.tok.lower() not in pat[1:]) or (pat[0] == "+" and chunk.tok.lower() in pat[1:]):
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
                if pat[0] == "-" and chunk.tok.lower() not in pat[1:]:
                    test_val == True
                else:
                    test_val == False
                if self.debug_p:
                    print "[chunkable_p](pat[0] == - and chunk.tok.lower() not in pat[1:]): %r" % (test_val)
            if (pat == []) or (pat[0] == "-" and chunk.tok.lower() not in pat[1:]) or (pat[0] == "+" and chunk.tok.lower() in pat[1:]):
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
            #chunk.__display__()
            yield(chunk)
            if chunk.chunk_end < self.len:
                #print "[chunk_iter]chunk_end: %i" % chunk.chunk_end
                chunk = self.chart[chunk.chunk_end]
            else:
                #print "[chunk_iter before break]chunk_end: %i" % chunk.chunk_end
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
                prev_n_string = prev_n_string + " ^"
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
    def section_loc(self, index):
        res = self.make_section_loc(self.field, self.num)
        return(fname("section_loc", res))

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
        res = self.chart[last_index].tok.lower()
        return(fname("last_word", res))
        
    @feature_method
    # tag signature (sequence of tags as a string)
    def tag_sig(self, index):
        res = "_".join(self.chart[index].chunk_tags)
        return(fname("tag_sig", res))

### language specific Sentence subclass definitions

class Sentence_english(Sentence):

    #print "Creating Sentence_english subclass"

    # previous verb
    # return closest verb to left of NP
    # as well as prep or particle if there is one after verb
    @feature_method
    def prev_V(self, index):
        verb = ""
        prep = ""
        verb_prep = ""
        i = index -1
        while i > 0:
            # terminate if verb is found
            if self.chart[i].tag[0] == "V":
                verb = self.chart[i].tok
                break
            # terminate if a noun is reached before a verb
            if self.chart[i].tag[0] == "N":
                break
            # keep a prep if reached before verb
            if self.chart[i].tag[0] in ["RP", "IN"]:
                prep = self.chart[i].tok
            else:
                # keep looking 
                i = i - 1
        if verb != "":
            verb_prep = verb + " " + prep
        res = verb_prep.lower()
        return(fname("prev_V", res))        

    # first noun to the left of chunk, within 3 words
    @feature_method
    def prev_N(self, index):
        noun = ""
        i = index - 1
        distance_limit = 3
        while i > 0 and distance_limit > 0:
            # terminate if verb is found
            if self.chart[i].tag[0] == "N":
                noun = self.chart[i].tok
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
        if self.chart[index].tag[0] == "J":
            res = self.chart[index].tok
        return(fname("chunk_lead_J", res))


    # initial V-ing verb in chunk, if there is one
    @feature_method
    def chunk_lead_VBG(self, index):
        res = ""
        if self.chart[index].tag[0] == "VBG":
            res = self.chart[index].tok
        return(fname("chunk_lead_VBG", res))

    # head of prep in chunk, if there is one
    @feature_method
    def of_head(self, index):
        res = ""
        i = index
        head = ""
        prep_idx = self.first_prep_idx(index)
        if prep_idx != -1:
            head_loc = prep_idx - 1
            head = self.chart[head_loc].tok
            res = head.lower()
        return(fname("of_head", res))

    # previous adj (JJ, JJR, JJS)
    # Adj must be immediately bfore index term
    @feature_method
    def prev_J(self, index):
        res = ""
        i = index - 1
        if self.chart[i].tag[0] == "J":
            res = self.chart[i].tok.lower()
        return(fname("prev_J", res))

    # first adjective in the chunk
    @feature_method
    def initial_J(self, index):
        res = ""
        i = index
        if self.chart[i].tag[0] == "J":
            res = self.chart[i].tok.lower()
        return(fname("initial_J", res))

    @feature_method
    def initial_V(self, index):
        res = ""
        i = index
        if self.chart[i].tag[0] == "V":
            res = self.chart[i].tok.lower()
        return(fname("initial_V", res))

    # If a prep occurs directly after the chunk, return the token
    @feature_method
    def following_prep(self, index):
        res = ""
        i = index
        following_index = self.chart[i].chunk_end
        if following_index <= self.last:
            if self.chart[following_index].tag == "IN":
                res = self.chart[following_index].tok.lower()
        return(fname("following_prep", res))        

class Sentence_german(Sentence):
    #print "Creating Sentence_german subclass"

class Sentence_chinese(Sentence):
    #print "Creating Sentence_chinese subclass"
    
    # first noun to the left of chunk, within 3 words
    @feature_method
    def prev_N(self, index):
        noun = ""
        i = index - 1
        distance_limit = 3
        while i > 0 and distance_limit > 0:
            # terminate if NN is found
            if self.chart[i].tag == "NN":
                noun = self.chart[i].tok
                break
            else:
                # keep looking 
                i = i - 1

            distance_limit = distance_limit - 1
        
        return(fname("prev_N", res))
    
    """
    #buggy feature, disabled 12/25/14 PGA
    @feature_method
    def penultimate_word (self, index):
        last_index = self.chart[index].chunk_end - 1
        if last_index ==0:
            return(fname("pen_word", ''))
        else:
            res = self.chart[last_index-1].tok
            return(fname("pen_word", res))
    """
        
    @feature_method
    def prev_V(self, index):
        verb = ""
        i = index -1
        while i > 0:
            # terminate if verb is found
            if self.chart[i].tag[0] == "V":
                verb = self.chart[i].tok
                break
            # terminate if a noun is reached before a verb
            if self.chart[i].tag[0] == "N":
                break
            """
            # keep a prep if reached before verb
            if self.chart[i].tag[0] in ["P", "IN"]:
                prep = self.chart[i].tok
            else:
                # keep looking
            """
            i = i - 1
        """
        if verb != "":
            verb_prep = verb + " " + prep
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
                res = self.chart[i].tok
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
                res = self.chart[i].tok
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
                measure = self.chart[i].tok
                if i > 1:
                    measure = measure + ' ' + self.chart[i-1].tok
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
                determiner = self.chart[i].tok
                break
            i = i - 1
        return(fname("prev_DT", determiner))

    """
    #previous PN within 3 words
    @feature_method
    def prev_PN(self, index):
        propN = ''
        i = index -1
        distance_limit = 3
        while i > 0 and distance_limit > 0:        
            # terminate if verb is found
            if self.chart[i].tag == "M":
                determiner = self.chart[i].tok
                break
            i = i - 1
        return(fname("prev_DT", determiner))

    """
### chunking

# chunking related classes
class Chunk:
    
    def __init__(self, tok_start, tok_end, tok, tag ):
        self.sid = -1  # sentence id (set in process_doc)
        self.tok_start = tok_start
        self.tok_end = tok_end
        self.tok = tok
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
        print "Chunk type: %s, phrase: %s, %i, %i" % (self.tag, self.phrase, self.chunk_start, self.chunk_end)



# instance of a chunk definition in the form of two dictionaries:
# conditions for matching the start of a chunk (tags + token constraints)
# conditions for continuing a chunk (tags + token constraints)
class chunkSchema:
    
    def __init__(self, start_pat, cont_pat, end_pat):
        self.d_start = {}
        self.d_cont = {}
        self.d_end = {}
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

# Chunk schema definitions
# constraints are indicated by 
# "-" none of the following strings
# "+" only the following strings
# [] no constraints
# end_pat are the legal POS that can end a chunk
#def chunk_schema_en():
def chunk_schema(lang):
    start_pat = []
    cont_pat = []
    end_pat = []
    
    if lang == "en":
        both_pat =  [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []], ["POS", []],  ["JJ", ["-", "further", "such", "therebetween", "same", "following", "respective", "first", "second", "third", "fourth", "respective", "preceding", "predetermined", "next", "more"] ], ["JJR", ["-", "more"] ], ["JJS", [] ], ["FW", ["-", "e.g.", "i.e"] ], ["VBG", ["-", "describing", "improving", "using", "employing",  "according", "resulting", "having", "following", "including", "containing", "consisting", "disclosing"]  ] ] 
        #start_pat = [ ["NN", ["-", "method"]] ] 
        start_pat = []
        cont_pat = [ ["NN", []], ["VBN", []], ["IN", ["+", "of"]], ["DT",  []], ["CC", []], ["RP", []] ]
        end_pat = [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []], ["VBG", ["-", "describing", "improving", "using", "employing", "according", "resulting", "having", "following", "including", "containing", "consisting", "disclosing", "pertaining", "being", "comprising", "corresponding"]  ] ]
        start_pat.extend(both_pat)
        cont_pat.extend(both_pat)

    elif lang == "de":
        start_pat =  [ ["NN", []], ["NE", []], ["ADJA", []] ]
        cont_pat = [ ["NN", []], ["EN", []], ["ADJA", []], ["APPR", ["+", "von"]], ["ART", ["+", "des", "der"]] ]
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
            fh = codecs.open("chunk_schema_%s.txt" % lang)
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                add_chunk_pattern_element(line, start_pat, cont_pat, end_pat)
    
        else:
            start_pat =  [ ["NN", []], ["NR", []], ["NT", []], ["JJ", []], ["VA", []] ]
            cont_pat = [ ["NN", []], ["NR", []], ["NT", []], ["JJ", []], ["VA", []], ["DEG", []], ["DEC", []] ]
            end_pat = [ ["NN", []]  ]
    
    cs = chunkSchema(start_pat, cont_pat, end_pat)
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
