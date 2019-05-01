# -*- coding: utf-8 -*-

"""

Wrappers for the Stanford tagger and segmenter.

"""

import sys, os
from subprocess import Popen, PIPE
import config


# To align sdp token nos with tokens starting at index 0, we need to add the
# token_no_offset of -1.  To use the sdp token numbering, set this to 0
token_no_offset = -1


os.environ['PYTHONIOENCODING'] = 'utf-8'


class Tagger:

    """Wrapper for the Standford tagger. Stanford tagger model options are listed at
    http://ufallab.ms.mff.cuni.cz/tectomt/share/data/models/tagger/stanford/README-Models.txt.

    We use the following:
        English: english-caseless-left3words-distsim.tagger
        Chinese: chinese.tagger
    """

    def __init__(self, model):
        self.stag_dir = config.STANFORD_TAGGER_DIR
        self.mx = config.STANFORD_MX
        self.tag_separator = config.STANFORD_TAG_SEPARATOR
        self.model = model
        self.verbose = False
        # Make the models directory explicit to fix a broken pipe error that
        # results when the entire models path is not specified. We are not using
        # "-outputFormatOptions lemmatize" because it does not work.
        tagger_jar = self.stag_dir + "/stanford-postagger.jar:"
        maxent_tagger = 'edu.stanford.nlp.tagger.maxent.MaxentTagger'
        model = "%s/models/%s" % (self.stag_dir, self.model)
        tag_separator_option = ""
        if self.tag_separator != "":
            tag_separator_option = " -tagSeparator " + self.tag_separator
        tagcmd = "java -mx%s -cp '%s' %s -model %s%s 2> tagger.log" % \
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


class Segmenter:

    """Wrapper for Standford segmenter for Chinese.

    Note: Large test file requires large memory usage.  For processing large
    data files, you may want to change memory allocation in Java e.g., to be
    able to use 8Gb of memory, you need to change the self.mx variable "8g".
    The default in the configuration file is "2000m."
    """

    def __init__(self):
        try:
            self.seg_dir = config.STANFORD_SEGMENTER_DIR
        except AttributeError:
            self.sdp_dir = "."
        try:
            self.mx = config.STANFORD_MX
        except AttributeError:
            self.mx = "300m"
        self.data_dir = self.seg_dir + "/data"
        self.verbose = False
        self.segcmd = self.segmenter_command()
        if self.verbose:
            print "[segWrapper init]segcmd: %s" % self.segcmd
        self.proc = Popen(self.segcmd, shell=True, stdin=PIPE, stdout=PIPE, universal_newlines=False)

    def segmenter_command(self):
        # make the models directory explicit
        # This fixes a broken pipe error that results when the entire models path is not specified.
        # Note that option: -outputFormatOptions lemmatize  does not work.
        # One issue is to read from stdin rather than from a file.  We use the linux solution described in
        # https://mailman.stanford.edu/pipermail/java-nlp-user/2012-July/002371.html
        # to set file to /dev/stdin
        return ('java -mx' + self.mx
                + ' -cp ' + self.seg_dir + '/seg.jar edu.stanford.nlp.ie.crf.CRFClassifier'
                + ' -sighanCorporaDict ' + self.data_dir
                + ' -testFile /dev/stdin -inputEncoding UTF-8'
                + ' -sighanPostProcessing true'
                + ' -keepAllWhitespaces false'
                + ' -loadClassifier ' + self.data_dir + '/ctb.gz'
                + ' -serDictionary ' + self.data_dir + '/dict-chris6.ser.gz 2> segmenter.log')

    def seg(self, text):
        self.give_input_and_end(text)
        result = self.get_output_to_end()
        return result
    
    def get_output_to_end(self):
        line = self.proc.stdout.readline()
        while is_ascii(line):
            line = self.proc.stdout.readline()
        line = line.decode(sys.stdout.encoding)
        return line

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
        if line is not None:
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


def is_ascii(s):
    return all(ord(c) < 128 for c in s)
