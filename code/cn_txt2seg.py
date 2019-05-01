"""cn_txt2seg.py

Create segmented chinese files formatted as follows:
- field headers of the form    FH_<name>:
- each followed by one or more lines of text (without any empty lines)
A line can consist of multiple sentences, which will be split by the tagger
Last line must be     END:

When embedded in other code, first create an instance of sdp.Segmenter and then
use the seg() funciton or the SegmenterWrapper class. See the end of those file
for an example of the latter.

When run from the command line, this script takes a list of files and runs each
of them through the segmenter, writing new files with the .seg extension:

    $ python cn_txt2seg.py FILE1 FILE2 ...

"""

import sys, re, codecs, StringIO
import sdp


DEBUG = False


def debug(debug_string):
    if DEBUG:
        print debug_string


# New version of segmenter, does some sentence splitting

class Segmenter(object):

    def __init__(self):
        self.segmenter = sdp.Segmenter()
        self.s_input = None
        self.s_output = None
        self.lines = []

    def process(self, infile, outfile, verbose=False):
        self.s_input = codecs.open(infile, encoding='utf-8')
        self.s_output = codecs.open(outfile, "w", encoding='utf-8')
        self.lines = []
        if verbose:
            print "[Segmenter] processing %s" % self.s_input.name
        for line in self.s_input:
            # a hack to get rid of the character with ordinal 12288
            # (CJK Character 0x3000 12288 IDEOGRAPHIC SPACE)
            line = ''.join([c for c in line if ord(c) != 12288])
            # this is needed because the segmenter has a normalization error for
            # non-breaking spaces, replace them here with regular spaces.
            line = line.replace(unichr(160), ' ').strip()
            if line != "":
                if line.startswith('FH_'):
                    self._segment_lines()
                    debug("[seg] header      [%s]" % line.strip())
                    self.s_output.write(line + u"\n")
                elif line.strip() == 'END':
                    self._segment_lines()
                    debug("[seg] end         [%s]" % line.strip())
                    self.s_output.write(line + u"\n")
                elif is_skipable(line):
                    self._segment_lines()
                    debug("[seg] skipable    [%s]" % line.strip())
                elif is_ascii(line):
                    self._segment_lines()
                    debug("[seg] ascii       [%s]" % line.strip())
                    self.s_output.write(line + u"\n")
                else:
                    debug("[seg] collecting  [%s]" % line.strip())
                    if line:
                        self.lines.append(line)
        self._segment_lines()
        self.s_input.close()
        self.s_output.close()

    def _segment_lines(self):
        if not self.lines:
            return
        text = (u" ".join(self.lines)).strip()
        split_text = split_cn(text).strip()
        split_text = split_text.split("\n")
        for split_line in split_text:
            line_length = len(split_line)
            if not line_length > 500:
                debug("[seg] segmenting  [%s]" % split_line)
                split_line = re.sub(r'^\s*$', '', split_line + "\n")
                if is_ascii(split_line):
                    self.s_output.write("%s" % split_line)
                else:
                    l_seg_string = self.segmenter.seg(split_line)
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

    (cn_comma, cn_period) = (u'\uff0c', u'\u3002')
    fh = StringIO.StringIO()
    text = text.strip()
    # this normalizes all whitespace, gets rid of linefeeds and other crap
    text = "\n".join(text.split())
    length = len(text)
    for i in range(length):
        c = text[i]
        if c == cn_period:
            fh.write(c + u"\n")
        elif c == "\n":
            pass
        else:
            fh.write(c)
    return_string = fh.getvalue()
    fh.close()
    return return_string


def seg(infile, outfile, segmenter):
    # Previous version of segmenter, keep around for now, but may be obsolete
    s_input = codecs.open(infile, encoding='utf-8')
    s_output = codecs.open(outfile, "w", encoding='utf-8')
    for line in s_input:
        line = re.sub(r'^\s*$', '', line)
        line = ''.join([c for c in line if ord(c) != 12288])
        debug("[tag]Processing line: %s\n" % line)
        if line != "":
            if is_omitable(line):
                s_output.write(line)
            else:
                # this is a hack needed because the segmenter has a normalization error
                # for non-breaking spaces, replace them here with regular spaces.
                line = line.replace(unichr(160), ' ')
                l_seg_string = segmenter.seg(line)
                if l_seg_string != '':
                    s_output.write("%s" % l_seg_string)
    s_input.close()
    s_output.close()


def is_omitable(s):
    """Do not segment anything over 500 characters or with ascii-8 only."""
    if len(s) > 500:
        return True
    return all(ord(c) < 256 for c in s)


if __name__ == '__main__':

    files_in = sys.argv[1:]
    sdp_segmenter = sdp.Segmenter()
    swrapper = Segmenter()
    use_old = False
    for file_in in files_in:
        file_out = file_in + '.seg'
        if use_old:
            seg(file_in, file_out, sdp_segmenter)
        else:
            swrapper.process(file_in, file_out, verbose=True)
