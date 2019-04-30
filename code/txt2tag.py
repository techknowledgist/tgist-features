"""txt2tag.py

Tagging text files

Files are formatted as follows:

- Field headers of the form "FH_<name>:"
- Each followed by one or more lines of text (without any empty lines)

A line can consist of multiple sentences, which will be split by the tagger

Last line must be 'END:'

"""

import codecs
import sdp

debug_p = False


# TODO: create a Tagger class that uses the language to initialize and then has the tag method
# TODO: check how that works with the Chinese tagger

def get_tagger(language):
    """Get the tagger appropriate for the language. Stanford tagger options are listed at
    http://ufallab.ms.mff.cuni.cz/tectomt/share/data/models/tagger/stanford/README-Models.txt)
    """
    if language == "en":
        return sdp.STagger("english-caseless-left3words-distsim.tagger")
    elif language == "cn":
        return sdp.STagger("chinese.tagger")
    else:
        exit("There is no tagger for language=%s" % language)


def tag(input_file, output_file, tagger):
    s_input = codecs.open(input_file, encoding='utf-8')
    s_output = open(output_file, "w")
    line_no = 0
    for line in s_input:
        line_no += 1
        if _skip_line(line):
            # TODO: maybe write these lines to the output but mark them somehow
            continue
        line = _fix_line(line)
        _debug("[tag] Processing line: %s\n" % line)
        if line != "":
            if line[0:3] == "FH_":
                # do not tag section headers
                line_out = line.encode('utf-8')
                s_output.write("%s\n" % line_out)
            else:
                _debug("[tag] line: %s" % line)
                _tag_line(line, line_no, tagger, s_output)
    s_input.close()
    s_output.close()


def _debug(text):
    if debug_p:
        print text


def _skip_line(line):
    """Very long lines typically contain non-textual garbage like gene sequences,
     skip them because some of them break the tagger.
    :param line:
    :return: True or False
    """
    return True if len(line) > 10000 else False


def _fix_line(line):
    """Several fixes to the line needed for the tagger."""
    line = line.strip("\n\r\f")
    # This is a hack to make the tagger work, but it loses information
    # TODO: could replace "~" with "&tilde;" or find the real solution
    line = line.replace('~','')
    # backspace characters break the sdp tagger code
    line = line.replace(unichr(8), '')
    return line


def _tag_line(line, line_no, tagger, s_output):
    try:
        l_tag_string = tagger.tag(line)
        _debug("[tag] line2: %s" % line)
        for tag_string in l_tag_string:
            tag_string = tag_string.encode('utf-8')
            _debug("[tag] tag_string: %s" % tag_string)
            s_output.write("%s\n" % tag_string)
    except Exception:
        print "WARNING: tagger error for line %d, skipping" % line_no
