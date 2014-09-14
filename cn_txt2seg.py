"""cn_txt2seg.py

Create segmented chinese files formatted as follows:
- field headers of the form    FH_<name>:
- each followed by one or more lines of text (without any empty lines)
A line can consist of multiple sentences, which will be split by the tagger
Last line must be     END:

When embedded in other code, first create an instance of sdp.Segmenter and then
use the seg() funciton or the SegmenterWrapper class. See the end of thos file
for an example of the latter.

When run from the command line, this script takes a list of files and runs each
of them through the segmenter, writing new files with the .seg extension:

    $ python cn_txt2seg.py FILE1 FILE2 ...

"""

import os, sys, re, codecs, StringIO
from time import sleep, time

import sdp

debug_p = False
#debug_p = True

def debug(debug_string):
    if debug_p:
        print debug_string


### Previous version of segmenter, keep around for now

#version to work with Popen --YZ
def seg(infile, outfile, segmenter):
    s_input = codecs.open(infile, encoding='utf-8')
    s_output = codecs.open(outfile, "w", encoding='utf-8')
    output = []
    t0 = time()
    t1 = None
    for line in s_input:
        line = re.sub(r'^\s*$', '', line)
        line = ''.join([c for c in line if ord(c) != 12288])
        if debug_p == True:
            print "[tag]Processing line: %s\n" % line
        if line != "":
            if is_omitable(line):
                s_output.write(line)
                #print "Omit: %s" %line
            else:
                # this is a hack needed because the segmenter has a normalization error
                # for non-breaking spaces, replace them here with regular spaces.
                line = line.replace(unichr(160),' ')
                #print type(line), line,
                l_seg_string = segmenter.seg(line)
                #if t1 is None: t1 = time
                if t1 is None:
                    t1 = time()
                    print "setting time"
                if l_seg_string != '':
                    s_output.write("%s" % l_seg_string)
    s_input.close()        
    s_output.close()
    print t1 - t0
    print time() - t1
    
def is_omitable(s):
    """Do not segment anything over 500 characters or with ascii-8 only."""
    if len(s) > 500:
        return True
    return all(ord(c) < 256 for c in s)


### New version of segmenter, does some sentence splitting

class SegmenterWrapper(object):

    def __init__(self, segmenter):
        self.segmenter = segmenter
        self.model_loaded = False

    def process(self, infile, outfile, verbose=False):
        self.s_input = codecs.open(infile, encoding='utf-8')
        self.s_output = codecs.open(outfile, "w", encoding='utf-8')
        self.lines = []
        self.t0 = time()
        self.t1 = None
        if verbose:
            print "[Segmenter] processing %s" % self.s_input.name
        for line in self.s_input:
            # a hack to get rid of the character with ordinal 12288
            line = ''.join([c for c in line if ord(c) != 12288])
            # this is needed because the segmenter has a normalization error for
            # non-breaking spaces, replace them here with regular spaces.
            line = line.replace(unichr(160),' ').strip()
            if line != "":
                if line.startswith('FH_'):
                    self._segment_lines(verbose)
                    debug("[seg] header      [%s]" % line.strip())
                    self.s_output.write(line + u"\n")
                elif line.strip() == 'END':
                    self._segment_lines(verbose)
                    debug("[seg] end         [%s]" % line.strip())
                    self.s_output.write(line + u"\n")
                elif is_skipable(line):
                    self._segment_lines(verbose)
                    debug("[seg] skipable    [%s]" % line.strip())
                elif is_ascii(line):
                    self._segment_lines(verbose)
                    debug("[seg] ascii       [%s]" % line.strip())
                    self.s_output.write(line + u"\n")
                else:
                    debug("[seg] collecting  [%s]" % line.strip())
                    if line:
                        self.lines.append(line)
        self._segment_lines(verbose)
        self.s_input.close()
        self.s_output.close()
        if verbose:
            print "[Segmenter] processing time is %d seconds" % (time() - self.t1)

    def _segment_lines(self, verbose):
        if not self.lines:
            return
        text = (u" ".join(self.lines)).strip()
        split_text = split_cn(text).strip()
        split_text = split_text.split("\n")
        for split_line in split_text:
            line_length = len(split_line)
            if not line_length > 500:
                debug("[seg] segmenting  [%s]" % split_line)
                #print "[%s]" % split_line, is_ascii(split_line)
                split_line = re.sub(r'^\s*$', '', split_line + "\n")
                if is_ascii(split_line):
                    self.s_output.write("%s" % split_line)
                else:
                    l_seg_string = self.segmenter.seg(split_line)
                    if self.t1 is None:
                        self.t1 = time()
                        if not self.model_loaded:
                            if verbose:
                                print "[Segmenter] model loaded in %d seconds" \
                                      % (self.t1 - self.t0)
                            self.model_loaded = True
                    self.s_output.write("%s" % l_seg_string)
        self.lines = []


def is_skipable(s):
    """Return True if this string is not worth segmenting."""
    s = s.strip()
    s = ''.join(s.split())
    length = len(s)
    # skip strings with > 5000 characters
    if length > 5000:
        return True
    # skip strings longer than 10 characters where more than 90% of the
    # characters are ascii characters
    ascii_chars = len([c for c in s if ord(c) < 256])
    if length > 0:
        ratio = ascii_chars/float(length)
        if length > 10 and ratio > 0.9:
            # print "%3d  %3d  %.2f  %s" % (ascii_chars , length, ratio, s)
            return True
    # skip short ascii only strings, except for numbers (this could also be the
    # date in FH_DATE)
    if ascii_chars == length and not s.isdigit():
        return True
    return False

def is_ascii(s):
    return all(ord(c) < 256 for c in s)


def split_cn(text):

    """A special split command for Chinese only. It is a rather simplistic
    version that first normalizes all whitespace with single \n characters
    and then splits on the Chinese period only, not using the \n character
    as an EOL marker."""

    # NOTE: this was copied from ../../utils/splitter because I have still not
    # figured out a good way to import things. In this case, appending ../.. to
    # sys.path and then importing utils.splitter clashed with the utils module
    # in this directory (at least, I think that that was the problem).

    (cn_comma, cn_period) = (u'\uff0c', u'\u3002')

    fh = StringIO.StringIO()
    text = text.strip()
    # this normalizes all whitespace, used to get rid of linefeeds and other crap
    text = "\n".join(text.split())
    length = len(text)
    for i in range(length):
        c = text[i]
        if c == cn_period: fh.write(c + u"\n")
        #elif c == cn_comma: fh.write(c + u"\n")
        elif c == "\n": pass
        else: fh.write(c)
    return_string = fh.getvalue()
    fh.close()
    return return_string


### Old deprecated (?) code

# cn_txt2seg.test_seg_cn()
def test_seg_cn():
    input = "/home/j/yzhou/patentWork/data/cn/txt/1999/CN1214051A.xml"
    output = "/home/j/yzhou/patentWork/data/cn/seg/1999/CN1214051A.xml"
    # segment using Stanford segmenter with chinese tree bank model
    segmenter = sdp.Segmenter()
    seg(input, output, segmenter)
    #segmenter.cn_segment_file(input, output)

def txt2seg_file(txt_file, seg_file, segmenter):
    segmenter.cn_segment_file(txt_file, seg_file, segmenter)

# segment all txts in source and place results in target dir
def txt2seg_dir(source_path, target_path, segmenter):
    for file in os.listdir(source_path):
        source_file = source_path + "/" + file
        target_file = target_path + "/" + file
        print "[txt2seg_dir]from %s to %s" % (source_file, target_file)
        #use seg() instead --YZ
        #segmenter.cn_segment_file(source_file, target_file)
        seg(source_file, target_file, segmenter)
    print "[txt2seg_dir]done"

# lang should be "cn"
def patent_txt2seg_dir(lang_path, language):
    segmenter = sdp.Segmenter()
    print "Allowing 10 seconds for segmenter to load stuff..."
    sleep(10)
    txt_path = lang_path + "/" + language + "/txt"
    seg_path = lang_path + "/" + language + "/seg"
    for year in os.listdir(txt_path):
        txt_year_dir = txt_path + "/" + year
        seg_year_dir = seg_path + "/" + year
        print "[patent_txt2seg_dir]calling txt2seg for dir: %s" % txt_year_dir
        txt2seg_dir(txt_year_dir, seg_year_dir, segmenter)
    print "[patent_txt2seg_dir]finished writing segmented data to %s" % seg_path

# top level call to tag txt data dir in a language
# cn_txt2seg.seg_lang("cn")
def seg_lang(lang):
    if lang == "cn":
        # we need to segment before tagging
        patent_path = "/home/j/anick/fuse/data/patents"
        patent_txt2seg_dir("/home/j/anick/fuse/data/patents", lang)



if __name__ == '__main__':

    files_in = sys.argv[1:]
    segmenter = sdp.Segmenter()
    swrapper = SegmenterWrapper(segmenter)
    use_old = False
    for file_in in files_in:
        file_out = file_in + '.seg'
        if use_old:
            seg(file_in, file_out, segmenter)
        else:
            swrapper.process(file_in, file_out, verbose=True)
