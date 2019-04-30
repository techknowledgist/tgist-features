# -*- coding: utf-8 -*-
"""
This is a simple wrapper for the Stanford Dependency Parser.

Upon initialization it opens a subprocess where it calls the SDP,
and it can be sent strings to parse using give_input()

Based on code from Amber Stubbs
astubbs@cs.brandeis.edu
last updated: August 25, 2009

Got the parser working for the case of generating tags, penn, and tdc output.
It would be better if the subprocess interaction were more robust.  Currently we
rely on the parser returning the expected format n order to complete reading output from 
subprocess.  It it hangs, look in log.dat for an error.
To make it robust, it might make sense to send stderr to stdout and check stdout for error messages. 
Send only debugging info to the log file.

"""

import sys, os
from subprocess import Popen, PIPE
import config


# debug_p value for sdpWrapper instance 
debug_p = 1

# To align sdp token nos with tokens starting at index 0, we need to add the
# token_no_offset of -1.  To use the sdp token numbering, set this to 0
token_no_offset = -1


os.environ['PYTHONIOENCODING'] = 'utf-8'


class STagger:

    """Wrapper for the Standford tagger.

    The model should be a file name in the tagger models subdirectory of
    self.stag_dir. The .props files contain properties of specific models
    (e.g. tagseparator). 

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

    st = sdp.STagger("english-caseless-left3words-distsim.tagger")

    The STagger works on Linux but does not work properly on Mac OSX. The right
    kind of string is handed in by give_input_and_end(), but when the method
    get_output_to_end() reads lines from the output pipe something is wrong with
    the encoding. In fact, the tagger itself must have gotten the wrong string
    since the tags are not correct.

    """

    def __init__(self, model):

        self.stag_dir = config.STANFORD_TAGGER_DIR
        self.mx = config.STANFORD_MX
        self.tag_separator = config.STANFORD_TAG_SEPARATOR
        self.model = model
        self.verbose = False

        if self.tag_separator != "":
            tag_separator_option = " -tagSeparator " + self.tag_separator + " "
        else:
            tag_separator_option = ""

        # Make the models directory explicit to fix a broken pipe error that
        # results when the entire models path is not specified. Note that
        # option: -outputFormatOptions lemmatize does not work.
        tagger_jar = self.stag_dir + "/stanford-postagger.jar:"
        maxent_tagger = 'edu.stanford.nlp.tagger.maxent.MaxentTagger'
        model = "%s/models/%s" % (self.stag_dir, self.model)
        tagcmd = "java -mx%s -cp '%s' %s -model %s%s  2>log.dat" % \
                 (self.mx, tagger_jar, maxent_tagger, model, tag_separator_option)
        if self.verbose:
            print "[stagWrapper init] \n$ %s" % tagcmd

        # create a subprocess that reads from stdin and writes to stdout
        self.proc = Popen(tagcmd, shell=True, stdin=PIPE, stdout=PIPE, universal_newlines=False)

    def tag(self, text):
        """returns a list of tagged sentence strings"""
        if self.verbose:
            print "[tag] text: %s" % text
        self.give_input_and_end(text)
        if self.verbose:
            print "[tag] after give_input_and_end"
        result = self.get_output_to_end()
        if self.verbose:
            print "[tag] after setting result to: %s" % result
        return result

    def give_input_and_end(self, text):
        """Passes a string to the sdp tagger subprocess. Adds a special termination
        string to use as a signal that tag output is finished."""
        terminated_line = text + u'\n~_\n'
        if self.verbose:
            print "[give_input_and_end] terminated_line: |%s|" % terminated_line
        self.proc.stdin.write(terminated_line.encode('utf-8'))
        self.proc.stdin.flush()

    def get_output_to_end(self):
        """Reads lines from the output of the subprocess (sdp parser) and returns them
        as a list of unicode strings. We use a line "~-" to signal the end of
        the output from the tagger. """

        result = []
        line = self.proc.stdout.readline()
        # Not sure why this is needed if this is called from pubmed.sh rather than 
        # fxml.test_pm() within python.  PGA
        if line is None:
            return result
        # now turn the stdout line, which is of type str, into a unicode string
        line = line.decode(sys.stdout.encoding)
        if self.verbose:
            print "[get_output_to_end] %s line is: |%s|" % (type(line).__name__, line)

        while True:
            # remove tabs from sdp output (e.g. for Phrase structure)
            line = line.strip("\n")
            line = line.lstrip()
            # The tagger will add a tag to the terminating line, so we match on
            # the first two characters only.
            if line[0:2] == "~_": 
                if self.verbose:
                    print "[get_output_to_end] found_terminator string, breaking from while loop"
                break
            if self.verbose:
                print "[get_output_to_end] in while loop"
                print "[get_output_to_end] appending line |%s|" % line
            if line != "":
                result.append(line)
            line = self.proc.stdout.readline().decode(sys.stdout.encoding)
            if self.verbose:
                print "[get_output_to_end] next %s line: |%s|" % (type(line).__name__, line)

        return result


# wrapper for Standford Chinese segmenter

"""
USAGE

Unix: 
> segment.sh [-k] [ctb|pku] <filename> <encoding> <size>
  ctb : Chinese Treebank
  pku : Beijing Univ.

filename: The file you want to segment. Each line is a sentence.
encoding: UTF-8, GB18030, etc. 
(This must be a character encoding name known by Java)
size: size of the n-best list (just put '0' to print the best hypothesis
without probabilities).
-k: keep all white spaces in the input

* Sample usage: segment.sh ctb test.simp.utf8 UTF-8

* Note: Large test file requires large memory usage.  For processing 
  large data files, you may want to change memory allocation in Java 
        (e.g., to be able to use 8Gb of memory, you need to change "-mx2g" 
        to "-mx8g" inside segment.sh). Another solution is to split the test 
        file to smaller ones to reduce memory usage.
"""


class Segmenter:

    def get_config(self):
        # use defaults in config.py
        # use try/except in case some defaults are not included
        # in config.py
        try:
            self.seg_dir = config.STANFORD_SEGMENTER_DIR
        except AttributeError:
            self.sdp_dir = "."
        try:
            self.mx = config.STANFORD_MX
        except AttributeError:
            self.mx = "300m"
        try:
            self.debug_p = config.STANFORD_DEBUG_P
        except AttributeError:
            self.debug_p = 0

        global debug_p
        debug_p = 0
        
    # model should be ctb (chinese using penn term bank model)

    def __init__(self):
        self.diff = 0
        self.get_config()
        self.data_dir = self.seg_dir + "/data"
        self.verbose = False

        # make the models directory explicit
        # This fixes a broken pipe error that results when the entire models path is not specified.
        # Note that option: -outputFormatOptions lemmatize  does not work.

        # One issue is to read from stdin rather than from a file.  We use the linux solution described in 
        # https://mailman.stanford.edu/pipermail/java-nlp-user/2012-July/002371.html
        # to set file to /dev/stdin

        self.segcmd = ('java -mx' + self.mx + ' -cp ' + self.seg_dir + '/seg.jar edu.stanford.nlp.ie.crf.CRFClassifier -sighanCorporaDict  '  + self.data_dir + ' -testFile /dev/stdin -inputEncoding UTF-8 -sighanPostProcessing true -keepAllWhitespaces false -loadClassifier ' + self.data_dir + '/ctb.gz -serDictionary ' + self.data_dir + '/dict-chris6.ser.gz 2>log.dat' )
        if self.verbose:
            print "[segWrapper init]segcmd: %s" % self.segcmd

        self.proc = Popen(self.segcmd, shell=True, stdin=PIPE, stdout=PIPE, universal_newlines = False)

    def seg(self, text):
        self.give_input_and_end(text)
        result = self.get_output_to_end()
        return result
    
    def is_ascii(self, s):
        return all(ord(c) < 128 for c in s)

    def get_output_to_end(self):
        line = self.proc.stdout.readline()
        while self.is_ascii(line):
            line = self.proc.stdout.readline()
        line = line.decode(sys.stdout.encoding)
        return line

    # NOT WORKIGN for seg
    # version that expects one line of output for one line of input
    def seg_w_popoen(self, text):
        if self.verbose:
            print "[process_to_end]text: %s" % text
        self.give_input_and_end(text)
        if self.verbose:
            print "[process_to_end]after give_input_and_end"
        result = self.get_output_to_end()
        return result

    # version without special terminator marker added.
    # passes a string to the sdp tagger subprocess
    # Also passes a special "~" string to use as a signal that tag output
    # is finished.
    def give_input_and_end(self, text):
        terminated_line = text
        if self.verbose:
            print "[give_input_and_end]terminated_line: |%s|" % terminated_line
        self.proc.stdin.write(terminated_line.encode('utf-8'))
        if self.verbose:
            print "[give_input_and_end]After proc.stdin.write"
        self.proc.stdin.flush()
        self.proc.stdin.write('\n')
        self.proc.stdin.write('\n')

    # Reads lines from the output of the subprocess (sdp parser) and 
    # concatenates them into a single string, returned as the result
    # We use a line with a single "~" to signal the end of the output
    # from the tagger.  Note that the tagger will add _<tag> to the tilda,
    # so we match on the first two characters only for the termination condition.
    def get_output_to_end_old(self):
        result = []
        line = self.proc.stdout.readline().decode('utf8')
        # Not sure why the != None is needed if this is called from pubmed.sh rather than
        #  fxml.test_pm() within python.  PGA
        if line != None:
            line = line.decode(sys.stdout.encoding)
        # remove tabs from sdp output (e.g. for Phrase structure)
        line = line.strip("\n")
        if self.verbose:
            print "[get_output_to_end]in while loop.  line: |%s|" % line
        # Append result only if line is not empty
        if line != "":
            result.append(line)
        if self.verbose:
            print "[get_output_to_end]result: |%s|" % result
        line = self.proc.stdout.readline().decode(sys.stdout.encoding)
        if self.verbose:
            print "[get_output_to_end]next line: |%s|" % line

        if self.verbose:
            print "[get_output_to_end]Out of loop.  Returning..."

        return result
