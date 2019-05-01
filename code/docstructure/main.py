"""

Main executable for the document structure parser.

Usage:

   % python main.py [OPTIONS] TEXT_FILE FACT_FILE STRUCTURE_FILE
   % python main.py [OPTIONS] XML_FILE TEXT_FILE TAGS_FILE FACT_FILE STRUCTURE_FILE
   % python main.py [-c COLLECTION] [-l LANGUAGE] FILE_LIST
   % python main.py [-c COLLECTION] [-l LANGUAGE] DIRECTORY
   % python main.py -t

In the first form, input is taken from TEXT_FILE, which contains the bare text, and
FACT_FILE, which contains some structural tags taken from the low-level BAE input
parser. The output is written to STRUCTURE_FILE, which has lines like the following

   SECTION ID=1 TYPE="UNLABELED" START=0 END=3978
   SECTION ID=2 TYPE="INTRODUCTION" TITLE="INTRODUCTION" START=3978 END=6016

In the second form, the input is an xml file and three intermediate files are created:
text file, tags file and facts file. As with form 1, the text file and the fact file are
then used to create the sect file. Both forms have the same options, all optional:

   [-h] [--debug] [-c COLLECTION] [-l LANGUAGE]

If the -h option is specified, html versions of the fact file and the sect file will be
created and saved as FACT_FILE.html and SECT_FILE.html.

The [-c COLLECTION] argument specifies the collection that the input document
was taken from. This can be used to overrule the default behaviour, which is to
scan the fact file and find the following line:

   DOCUMENT COLLECTION="$COLLECTION"

In this line, $COLLECTION is one of WEB_OF_SCIENCE, LEXISNEXIS, PUBMED,
ELSEVIER, and CNKI.

Simliarly, with [-l LANGUAGE} the language can be handed in as an
argument. Values are 'ENGLISH', 'GERMAN' and 'CHINESE'. As with the collection,
the default behaviour is to scan the fact file if there is one, searching for

   DOCUMENT LANGUAGE="ENGLISH|CHINESE|GERMAN"

In the third form, the input and output files are specified in the file
FILE_LIST. In the fourth form, all pairs of .txt and .fact files in DIRECTORY
are processed and .sect files are created. Both these forms have the -l and -c
options, but the -h option will be ignored. In both cases, whether the oprions
are specified or not, the language and collection are assumed to be the saem for
all files in the list or directory.

Finally, in the fifth form, a simple sanity check is run, where four files (one
pubmed, one mockup Elsevier, one mockup WOS and one patent) are processed and
the diffs between the resulting .sect files and the regression files are printed
to the standard output.

If the code fails the regression test, the coder is responsible for checking why
that happened and do one of two things: (i) change the code if a bug was
introduced, (ii) update the files in data/regression if code changes introduced
legitimate changes to the output.

"""


import os, sys, re, getopt, difflib
import pubmed, lexisnexis, cnki
import utils.view
from utils.xml import transform_tags_file
from utils.misc import run_shell_commands

# Note, these aren't used here but imported from main in other modules
from readers.common import load_data, open_write_file


DEBUG = False


def usage():
    print "\nUsage:"
    print '  % python main.py [-h] [-c COLLECTION] [-l LANGUAGE] ' \
          + 'TEXT_FILE FACT_FILE STRUCTURE_FILE'
    print '  % python main.py [-h] [-c COLLECTION] [-l LANGUAGE] ' \
          + 'XML_FILE TEXT_FILE TAGS_FILE FACT_FILE STRUCTURE_FILE'
    print '  % python main.py [-c COLLECTION] [-l LANGUAGE] FILE_LIST'
    print '  % python main.py [-c COLLECTION] [-l LANGUAGE] DIRECTORY'
    print '  % python main.py -o [-l LANGUAGE] XML_FILE TEXT_FILE ' \
          + 'TAGS_FILE FACT_FILE STRUCTURE_FILE ONTO_FILE'
    print '  % python main.py -t'


def create_fact_file(xml_file, text_file, tags_file, fact_file):
    """Given an xml file, first create text and tags files using the xslt standoff scripts and
    then create a fact file."""
    # TODO: find a better way to do this, I want to use execfile to put the document
    # parser into a namespace, but then the __file__ variable is not available anymore
    dirname = os.path.dirname(__file__)
    text_xsl = os.path.join(dirname, 'utils/standoff/text-content.xsl')
    tags_xsl = os.path.join(dirname, 'utils/standoff/standoff.xsl')
    commands = [
        "xsltproc %s %s > %s" % (text_xsl, xml_file, text_file),
        "xsltproc %s %s | xmllint --format - > %s" % (tags_xsl, xml_file, tags_file)]
    run_shell_commands(commands)
    transform_tags_file(tags_file, fact_file)


class Parser(object):

    def __init__(self):
        self.test_mode = False
        self.html_mode = False
        self.onto_mode = False
        self.collection = None
        self.language = None

    def __str__(self):
        return "<Parser for %s on %s>" % (self.language, self.collection)

    def process_file(self, text_file, fact_file, sect_file, fact_type='BAE', verbose=False):
        """
        Takes a text file and a fact file and creates a sect file with the section data.
        The data in fact_file can have two formats: (i) the format generated by the BAE
        wrapper with fact_type=BAE and (ii) the format generated by utils/standoff with
        fact_type=BASIC. """
        self._create_factory(text_file, fact_file, sect_file, fact_type, verbose)
        try:
            self.factory.make_sections()
            self.factory.print_sections()
            if self.html_mode:
                fact_file_html = 'data/html/' + os.path.basename(fact_file) + '.html'
                sect_file_html = 'data/html/' + os.path.basename(sect_file) + '.html'
                utils.view.createHTML(text_file, fact_file, fact_file_html)
                utils.view.createHTML(text_file, sect_file, sect_file_html)
            # self.factory.print_hierarchy()
        except UserWarning:
            print 'WARNING:', sys.exc_value

    def process_xml_file(self, xml_file, text_file, tags_file, fact_file, sect_file,
                         verbose=False, debug=True):
        """
        Takes an xml file and creates sect file, while generating some intermediate data."""
        if debug:
            global DEBUG
            DEBUG = True
        create_fact_file(xml_file, text_file, tags_file, fact_file)
        self.process_file(text_file, fact_file, sect_file, fact_type='BASIC', verbose=verbose)
        # cleanup intermediary files, to keep them, use the --debug option
        if not DEBUG:
            for filename in (text_file, tags_file, fact_file):
                os.remove(filename)

    def process_directory(self, path):
        """
        Processes all files in a directory with text and fact files. Takes all .txt files,
        finds sister files with extension .fact and then creates .sect files."""
        # TODO: add --xml option for directories with only xml files
        text_files = []
        fact_files = {}
        for f in os.listdir(path):
            if f.endswith('.txt'):
                text_files.append(f)
            if f.endswith('.fact'):
                fact_files[f] = True
        total_files = len(text_files)
        file_number = 0
        print "Processing %d files" % total_files
        for text_file in text_files:
            file_number += 1
            fact_file = text_file[:-4] + '.fact'
            sect_file = text_file[:-4] + '.sect'
            if fact_files.has_key(fact_file):
                text_file = os.path.join(path, text_file)
                fact_file = os.path.join(path, fact_file)
                sect_file = os.path.join(path, sect_file)
                print "Processing %d of %d: %s" % (file_number, total_files, text_file[:-4])
                self.process_file(text_file, fact_file, sect_file)

    def process_files(self, file_list):
        """
        Takes a file with names of input and output files and processes them. Each line in the
        file has three filenames, separated by tabs, the first file is the text inut file, the
        second the fact input file, and the third the output file."""
        # TODO: may want to extend this to XML files
        for line in open(file_list):
            (text_file, fact_file, sections_file) = line.strip().split()
            #bprint "Processing  %s" % (text_file[:-4])
            self.process_file(text_file, fact_file, sections_file)

    def _create_factory(self, text_file, fact_file, sect_file, fact_type, verbose=False):
        """
        Returns the factory needed given the collection parameter and specifications in the
        fact file and, if needed, some characteristics gathered from the text file."""
        self._determine_collection(fact_file)
        if self.collection == 'PUBMED':
            self.factory = pubmed.BiomedNxmlSectionFactory(
                text_file, fact_file, sect_file, fact_type, self.language, verbose)
        elif self.collection == 'LEXISNEXIS':
            self.factory = lexisnexis.PatentSectionFactory(
                text_file, fact_file, sect_file, fact_type, self.language, verbose)
        elif self.collection == 'CNKI':
            self.factory = cnki.CnkiSectionFactory(
                text_file, fact_file, sect_file, fact_type, self.language, verbose)
        else:
            raise Exception("No factory could be created")

    def _determine_collection(self, fact_file):
        """
        Loop through the fact file in order to find the line that specifies the collection."""
        if self.collection is None:
            expr = re.compile('DOCUMENT.*COLLECTION="(\S+)"')
            for line in open(fact_file):
                result = expr.search(line)
                if result is not None:
                    self.collection = result.group(1)
                    break

    def ping(self):
        """Utility method to quickly see if it work, useful when calling this module from
        the outside."""
        self.collection = 'LEXISNEXIS'
        xml_file = "data/in/lexisnexis/US4192770A.xml"
        text_file = "data/tmp/US4192770A.txt"
        tags_file = "data/tmp/US4192770A.tags"
        fact_file = "data/tmp/US4192770A.fact"
        sect_file = "data/tmp/US4192770A.sect"
        self.process_xml_file(xml_file, text_file, tags_file, fact_file, sect_file)
        print "Created", sect_file

    def run_tests(self):
        """
        Runs a regression test on a couple of files. For all these files, there needs to
        be a sect file in data/regression and xml or txt/fact files in data/in in one of
        the four source directories."""
        files = (
            ('pubmed', 'f401516f-bd40-11e0-9557-52c9fc93ebe0-001-gkp847'),
            ('pubmed', 'pubmed-mm-test'),
            ('lexisnexis', 'US4192770A'),
            ('lexisnexis', 'US4192770A.xml'),
            ('lexisnexis', 'US4504220A')
            )
        results = []
        self.html_mode = True
        for collection, filename in files:
            self.run_test(collection, filename, results)
        for filename, sect_file, response, key_file, key in results:
            print "\n[%s]" % filename,
            diff = difflib.unified_diff(response, key, fromfile=sect_file, tofile=key_file)
            differences = count_iterable(diff)
            if differences == 0:
                print "... \033[0;32mPassed\033[0m"
            else:
                print "... \033[0;31mFailed\033[0m"
                print "\n   Differences in"
                print '     ', sect_file
                print '     ', key_file
            # for line in difflib.unified_diff(response, key, fromfile=sect_file, tofile=key_file):
            #    sys.stdout.write(line)
        print

    def run_test(self, collection, filename, results):
        # reset the collection every iteration, we are not using the collection argument
        # on purpose because we want to also test whether the code finds the collection in
        # the fact file
        self.collection = None
        if filename.endswith('.xml'):
            self.run_test_with_basic_input(collection, filename, results)
        else:
            self.run_test_with_bae_input(collection, filename, results)

    def run_test_with_basic_input(self, collection, filename, results):
        self.collection = 'LEXISNEXIS'
        xml_file = "data/in/%s/%s" % (collection, filename)
        text_file = "data/tmp/%s.txt" % filename
        tags_file = "data/tmp/%s.tags" % filename
        fact_file = "data/tmp/%s.fact" % filename
        sect_file = "data/out/%s.sect.basic" % filename
        key_file ="data/regression/%s.sect" % filename
        self.process_xml_file(xml_file, text_file, tags_file, fact_file, sect_file)
        response = open(sect_file).readlines()
        key = open(key_file).readlines()
        results.append((filename, sect_file, response, key_file, key))

    def run_test_with_bae_input(self, collection, filename, results):
        text_file = "data/in/%s/%s.txt" % (collection, filename)
        fact_file = "data/in/%s/%s.fact" % (collection, filename)
        sect_file = "data/out/%s.sect.bae" % filename
        key_file = "data/regression/%s.sect" % filename
        self.process_file(text_file, fact_file, sect_file)
        response = open(sect_file).readlines()
        key = open(key_file).readlines()
        results.append((filename, sect_file, response, key_file, key))


def restore_sentences(f, data_to_write):
    """Chinese data seem to be created using OCS and have <br> all over the place, often
    splitting segments. Since the segmenter takes one line at the time, we spend some time
    here glueing together the parts of sentences."""
    return_data = ""
    empty_line = False
    for line in data_to_write.split("\n"):
        line = line.strip()
        if line:
            empty_line = False
            return_data += line
        else:
            if not empty_line:
                return_data += "\n"
            empty_line = True
    return split_chinese_paragraph(return_data)


def split_chinese_paragraph(text):
    """Splits a chinese text string. Simply scans for split
    characters, currently just the chinese period."""
    chinese_split_chars = [u'\u3002']  # just the period
    sentences = []
    collected = []
    for c in text:
        collected.append(c)
        if c in chinese_split_chars:
            sentences.append(u''.join(collected))
            collected = []
    if collected:
        sentences.append(u''.join(collected))
    return u"\n".join(sentences)


def restore_proper_capitalization(text):
    """Up to 1991, German titles are all caps, which causes the tagger to recognize them
    as a string of proper nouns. The quickest fix to get decent tagging was to go to
    initial caps for all words. Do not do anything is the text is not all upper."""
    return text.lower().title() if text.isupper() else text


def count_iterable(i):
    """Returns the length of an iterable."""
    return sum(1 for x in i)


if __name__ == '__main__':

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], 'htc:l:', ['debug'])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    parser = Parser()
    for opt, val in opts:
        if opt == '-t': parser.test_mode = True
        elif opt == '-h': parser.html_mode = True
        elif opt == '-c': parser.collection = val
        elif opt == '-l': parser.language = val
        elif opt == '--debug': DEBUG = True

    # run some simple tests
    if parser.test_mode:
        parser.run_tests()

    # process a text file and a fact file, creating a sect file
    elif len(args) == 3:
        text_file, fact_file, sect_file = args
        parser.process_file(text_file, fact_file, sect_file, verbose=False)

    # process an xml file, creating txt file, tags file, fact file and sect file
    elif len(args) == 5:
        xml_file, txt_file, tags_file, fact_file, sect_file = args
        parser.process_xml_file(xml_file, txt_file, tags_file, fact_file, sect_file,
                                verbose=False)

    # process multiple files listed in an input file or the contents of a directory
    elif len(args) == 1:
        path = args[0]
        if os.path.isdir(path):
            parser.process_directory(path)
        elif os.path.isfile(path):
            parser.process_files(path)

    # by default
    else:
        text_file = "doc.txt"
        fact_file = "doc.fact"
        sect_file = "doc.sections"
        parser.collection = 'PUBMED'
        parser.process_file(text_file, fact_file, sect_file, verbose=False)
