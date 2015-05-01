# xml2txt
# module to create a fielded text file from an xml (patent) file
# top level call: patents_xml2txt(patent_path, lang)

import os, sys, re, codecs, pdb, StringIO
from xml.dom.minidom import parse, Node

script_path = os.path.abspath(sys.argv[0])
script_dir = os.path.dirname(script_path)
os.chdir(script_dir)
os.chdir('../..')
sys.path.insert(0, os.getcwd())
os.chdir(script_dir)

from utils.docstructure.main import Parser, create_fact_file, open_write_file
from utils.docstructure.main import load_data, restore_sentences
from ontology.utils.misc import findall

TARGET_FIELDS = ['FH_TITLE', 'FH_DATE', 'FH_ABSTRACT', 'FH_SUMMARY',
                 'FH_TECHNICAL_FIELD', 'FH_BACKGROUND_ART',
                 'FH_DESC_REST', 'FH_FIRST_CLAIM', 'FH_OTHER_CLAIMS']

USED_FIELDS = TARGET_FIELDS + ['FH_DESCRIPTION']

# all the fields that should only have one element in their list
SINGLETON_FIELDS = TARGET_FIELDS[:-1]

MAPPINGS = { 'META-TITLE': 'FH_TITLE',
             'META-DATE': 'FH_DATE',
             'ABSTRACT': 'FH_ABSTRACT',
             'SUMMARY': 'FH_SUMMARY',
             'DESCRIPTION': 'FH_DESCRIPTION',
             'TECHNICAL_FIELD': 'FH_TECHNICAL_FIELD',
             'BACKGROUND_ART': 'FH_BACKGROUND_ART' }

DEBUG = False

tm = u'\u2122'

opentag_idx = {}
closetag_idx = {}


def print_tags():
    print "OPENTAGS"
    for t, c in opentag_idx.items():
        print "  %4d  '%s'" % (c, t)
    print "CLOSETAGS"
    for t, c in closetag_idx.items():
        print "  %4d  '%s'" % (c, t)


def xml2txt(xml_parser, source, source_file, target_file, workspace):
    """Create a target_file in the d1_txt directory from a source_file in the
    xml directory. This includes some cleaning of the source file by adding some
    spaces, see clean_file() and clean_tag() for more details."""
    basename = os.path.basename(target_file)
    cleaned_source_file = os.path.join(workspace, "%s.clean" % basename)
    clean_file(source_file, cleaned_source_file, opentag_idx, closetag_idx)
    if source == 'ln':
        ds_text_file = os.path.join(workspace, "%s.text" % basename)
        ds_tags_file = os.path.join(workspace, "%s.tags" % basename)
        ds_fact_file = os.path.join(workspace, "%s.fact" % basename)
        ds_sect_file = os.path.join(workspace, "%s.sect" % basename)
        create_fact_file(cleaned_source_file, ds_text_file, ds_tags_file, ds_fact_file)
        xml_parser.collection = 'LEXISNEXIS'
        xml_parser.process_file(ds_text_file, ds_fact_file, ds_sect_file, fact_type='BASIC')
        (text, section_tags) = load_data(ds_text_file, ds_sect_file)
        fh_data = {}
        for f in USED_FIELDS:
            fh_data[f] = []
        add_sections(xml_parser, section_tags, text, fh_data)
        write_sections(xml_parser, target_file, fh_data)
        for fname in (ds_text_file, ds_tags_file, ds_fact_file, ds_sect_file):
            os.remove(fname)
    # for wos, cnki and pubmed we ignore the xml_parser that was handed in because we
    # can use a simpler and faster one
    elif source == 'wos':
        parse_wos_doc(cleaned_source_file, target_file)
    elif source == 'cnki':
        CNKIDoc(source_file, target_file).xml2txt()
    elif source == 'pm':
        PubMedDoc(source_file, target_file).xml2txt()
    os.remove(cleaned_source_file)


def add_sections(xml_parser, section_tags, text, fh_data):
    """Collect all the tags that have a mapping or that are claims. Then remove embedded
    tags and add content to the FH_DESC_REST section."""
    for stag in section_tags:
        (p1, p2, tagtype) = (stag.start_index, stag.end_index, stag.attr('TYPE'))
        section = (p1, p2, text[int(p1):int(p2)].strip())
        if MAPPINGS.get(tagtype) is not None:
            add_mapped_tagtype(xml_parser, stag, fh_data, p1, p2, tagtype, section)
        elif tagtype == 'CLAIM':
            add_claim(fh_data, stag, section)
    remove_embedded_section(fh_data)
    populate_desc_rest(fh_data, text)

def write_sections(xml_parser, target_file, fh_data):
    """Write the sections as requested by the technology tagger to a file."""
    onto_fh = open_write_file(target_file)
    for f in TARGET_FIELDS:
        if fh_data.has_key(f) and fh_data[f]:
            onto_fh.write(u"%s:\n" % f)
            for sect in fh_data[f]:
                data_to_write = sect[2]
                if xml_parser.language == 'CHINESE':
                    data_to_write = restore_sentences(f, data_to_write)
                onto_fh.write(data_to_write)
                onto_fh.write(u"\n")
    onto_fh.write("END\n")
    
def populate_desc_rest(fh_data, text):
    """Create the content of FH_DESC_REST, which has the parts of the description that are
    not in the summary, technical field or backhruond art. A summary is used for English
    patents. Chinese patents can have the background art and/or technical field
    sections."""
    desc = get_first(fh_data, 'FH_DESCRIPTION')
    summ = get_first(fh_data, 'FH_SUMMARY')
    tech = get_first(fh_data, 'FH_TECHNICAL_FIELD')
    back = get_first(fh_data, 'FH_BACKGROUND_ART')
    if desc and summ:
        fh_data['FH_DESC_REST'].append((summ[1], desc[1], text[summ[1]:desc[1]].strip()))
    elif desc and tech and back:
        fh_data['FH_DESC_REST'].append((back[1], desc[1], text[back[1]:desc[1]].strip()))
    elif desc and back:
        fh_data['FH_DESC_REST'].append((back[1], desc[1], text[back[1]:desc[1]].strip()))
    elif desc and tech:
        fh_data['FH_DESC_REST'].append((tech[1], desc[1], text[tech[1]:desc[1]].strip()))
    elif desc:
        fh_data['FH_DESC_REST'].append((desc[0], desc[1], text[desc[0]:desc[1]].strip()))

def add_mapped_tagtype(xml_parser, section_tag, fh_data, p1, p2, tagtype, section):
    """Add a section tag for those tags whose tagtype are mapped to one of the FH_*
    fields used by the technology tagger."""
    mapped_type = MAPPINGS[tagtype]
    # Skip the title or abstract if it is in English and the language set is
    # German or Chinese. TODO: needs to be generalized to all languages.
    if xml_parser.language != 'ENGLISH' and tagtype in ('META-TITLE', 'ABSTRACT'):
        if section_tag.attr('LANGUAGE') == 'eng':
            return        
    # ad hoc fix for german
    if mapped_type == 'FH_TITLE' and xml_parser.language == 'GERMAN':
        section[2] = restore_proper_capitalization(section[2])
    if DEBUG:
        print_section(section, mapped_type)
    fh_data[mapped_type].append(section)
    
def add_claim(fh_data, section_tag, section):
    """Add a claim section, distinguishing between first claim and other claims."""
    if section_tag.attr('CLAIM_NUMBER') == '1':
        if DEBUG:
            print_section(section, 'FH_FIRST_CLAIM')
        fh_data['FH_FIRST_CLAIM'].append(section)
    else:
        if DEBUG:
            print_section(section, 'FH_OTHER_CLAIMS')
        fh_data['FH_OTHER_CLAIMS'].append(section)

def remove_embedded_section(fh_data):
    """Remove all the embedded tags. For example, it is quite common for there
    to be a summary inside of a summary (where there is a summary tag and within
    it a 'Summary of the Invention' heading). Rather simplistic way of doing
    this, just keep the first summary and description section. Should really
    loop over all elements and check whether they are embedded in any other
    element."""
    for tagtype in SINGLETON_FIELDS:
        fh_data[tagtype] = fh_data[tagtype][:1]

def get_first(fh_data, field):
    return fh_data[field][0] if fh_data[field] else None
    
def print_section(section, prefix=''):
    if prefix:
        print prefix,
    print section[0], section[1], section[2][:50]


# Some methods to clean the input before XML parsing

def clean_file(source_file, cleaned_source_file, opentag_idx, closetag_idx):
    """A method to perform various cleaning operations of the source file. Now
    mostly concentrates on two things: removing the trademark symbol and adding
    spaces before and after some xml tags."""
    fh_in = codecs.open(source_file, encoding="utf-8")
    fh_out = codecs.open(cleaned_source_file, 'w', encoding="utf-8")
    for line in fh_in:
        #_store_tag_statistics(line, opentag_idx, closetag_idx)
        if line.find(tm) > -1:
            line = remove_trademark(line)
        if line.find('claim-text') > -1:
            # insert a linefeed and not a newline because the source data has
            # the former
            line = clean_tag(line, 'claim-text', "\l")
        if line.find('claim-ref') > -1:
            line = clean_tag(line, 'claim-ref', ' ')
        if line.find('figref') > -1:
            line = clean_tag(line, 'figref', ' ')
        fh_out.write(line)

def _store_tag_statistics(line, opentag_idx, closetag_idx):
    """Store some tag statistics in the two indexes. This could be used later on
    when we try to be a bit smarter on where to insert spaces."""
    pat1 = re.compile('.<[^/][^>]+>')
    pat2 = re.compile('</[^>]+>.')
    result1 = pat1.findall(line)
    result2 = pat2.findall(line)
    for r in result1:
        r = r.replace("\n", ' ')
        if r[0] != ' ':
            opentag_idx[r] = opentag_idx.get(r, 0) + 1
    for r in result2:
        r = r.replace("\n", ' ')
        r = r.replace("\r", ' ')
        if r[-1] != ' ':
            closetag_idx[r] = closetag_idx.get(r, 0) + 1

def remove_trademark(line):
    return line.replace(tm, '')

def clean_tag(line, tag, insert):
    """Clean a tag by surrounding it by spaces if needed. This turned out to be
    needed because in the source data there are many occurrences where the text
    inside figref, claim-ref and claim-text tags is not separated from the text
    outside by a space or newline and the tag itself is the only separator. This
    results in weird terms like 'AndFIG' and '1shows' coming out of a string
    like 'And<figref>FIG 1</figref>shows an...'."""
    open_tag = "<%s>" % tag
    close_tag = "</%s>" % tag
    idxs = findall(line, open_tag)
    if idxs:
        line = add_space_before(line, idxs, insert)
        #print line
    idxs = findall(line, close_tag)
    if idxs:
        line = add_space_after(line, idxs, close_tag, insert)
        #print line
    return line

def add_space_before(line, idxs, insert):
    output = StringIO.StringIO()
    idx = -1
    for c in line:
        idx += 1
        if idx in idxs and idx > 0 and not line[idx-1].isspace():
            #print "Adding space before: [%s]" % (line[idx:idx+20])
            output.write(insert)
        output.write(c)
    return output.getvalue()

def add_space_after(line, idxs, tag_string, insert):
    step = len(tag_string)
    output = StringIO.StringIO()
    idx = -1
    for c in line:
        idx += 1
        if idx - step in idxs and idx < len(line) and line[idx].isalnum():
            #print "Adding space after: [%s] and before [%s]" % \
            #      (line[idx-20:idx], line[idx:idx+20])
            output.write(insert)
        output.write(c)
    return output.getvalue()


STATS_TITLES = []
STATS_DATES = {}

def print_stats():
    print "\n".join(STATS_TITLES)
    for k,v in STATS_DATES.items(): print k, v


def parse_wos_doc(cleaned_source_file, target_file):
    fh_in = codecs.open(cleaned_source_file)
    fh_out = codecs.open(target_file, 'w')
    title = None
    year = None
    abstract = None
    for line in fh_in:
        if line.startswith('<item_title'):
            title = line.strip()[12:-13]
            STATS_TITLES.append(title)
        if line.startswith('<bib_date'):
            year_idx = line.find('year="')
            year = line[year_idx+6:year_idx+10]
            STATS_DATES[year] = STATS_DATES.get(year, 0) + 1
        if line.startswith('<p>'):
            abstract = line.strip()[3:-4]
    fh_out.write("FH_DATE:\n%s\n" % year)
    fh_out.write("FH_TITLE:\n%s\n" % title)
    fh_out.write("FH_ABSTRACT:\n%s\nEND\n" % abstract)



class CNKIDoc(object):
    
    def __init__(self, source_file, target_file, metadata=None):
        self.source = source_file
        self.target = target_file
        self.metadata = metadata
        self.year = self.get_year()
        self.text = codecs.open(self.source, encoding='utf8').read()
        self.title = self.get_title()
        self.abstract = self.get_abstract()
        self.body = self.get_body()
        self.stuff = self.get_stuff()

    def __str__(self):
        return "<CNKIDoc year=%s fname=%s>" % (self.year, os.path.basename(self.source))

    def xml2txt(self):
        #print len(self.title), len(self.abstract), len(self.body)
        #if self.title: print self.title
        fh = codecs.open(self.target, 'w', encoding='utf8')
        if self.title: fh.write(u"FH_TITLE:\n%s\n" % self.title)
        if self.year: fh.write(u"FH_DATE:\n%s\n" % self.year)
        if self.abstract: fh.write(u"FH_ABSTRACT:\n%s\n" % self.abstract)
        if self.body: fh.write(u"FH_BODY:\n%s\n" % self.body)
        if self.stuff: fh.write(u"FH_STUFF:\n%s\n" % self.stuff)

    def get_title(self):
        return self.get_tag('fs:ArticleTitle lang="zh"')

    def get_abstract(self):
        return self.get_tag('fs:AbstractBlock lang="zh"')
        
    def get_body(self):
        """Return the document text body. If there are no body tags, the empty
        string is returned."""
        return self.get_tag('fs:Body')

    def get_stuff(self):
        return self.get_tag('fs:Stuff')

    def get_tag(self, tagname):
        taglen = len(tagname) + 2
        opentag = "<%s>" % tagname
        closetag = "</%s>" % tagname.split()[0]
        idx1 = self.text.find(opentag)
        idx2 = self.text.find(closetag)
        if idx1 == -1 or idx2 == -1:
            return ''
        return self.text[idx1+taglen:idx2]

    def get_year(self):
        """Get the year from the name of the file."""
        year = ''
        for c in os.path.basename(self.source):
            if c.isdigit():
                year += c
            if len(year) == 4:
                return year


def is_chinese(c):
    """Return True if c is a Chinese character, return False otherwise. This is
    based in a range of chinese characters"""
    # TODO: check with Si Li what is included
    return c >= u'\u4e00' and c <= u'\u9fa5'


class PubMedDoc(object):

    """Simple document parser for Pubmed documents."""

    # Note that this is based on code written for a different project, but
    # forked off and made independent.

    def __init__(self, xmlfile, txtfile):
        self.fname = xmlfile
        self.outfile = txtfile
        self.dom = parse(xmlfile)
        self.title = None
        self.journal = None
        self.subject = None
        self.year = None
        self.abstract = []
        self.paragraphs = []
        self._set_title()
        self._set_journal()
        self._set_subject()
        self._set_year()
        self._set_paragraphs()

    def __str__(self):
        return "<PubMedDoc '%s'>" % self.fname

    def _set_title(self):
        titles = self.dom.getElementsByTagName('article-title')
        for title in titles:
            if title.parentNode.tagName == 'title-group':
                self.title = title.firstChild.nodeValue

    def _set_journal(self):
        self.journal = self.fname.split(os.sep)[-2]

    def _set_subject(self):
        subjects = self.dom.getElementsByTagName('subject')
        for subject in subjects:
            if subject.parentNode.tagName == 'subj-group':
                self.subject = subject.firstChild.nodeValue

    def _set_year(self):
        def in_pubdate(n): return n.parentNode.tagName == 'pub-date'
        years = [y for y in self.dom.getElementsByTagName('year') if in_pubdate(y)]
        for y in years:
            year = int(y.firstChild.nodeValue)
            if self.year is None or year < self.year:
                self.year = year

    def _set_paragraphs(self):
        pnodes = self.dom.getElementsByTagName('p')
        for p in pnodes:
            parent_tag = p.parentNode.tagName
            grandparent_tag = p.parentNode.parentNode.tagName
            ptext = ''
            for n1 in p.childNodes:
                if n1.nodeType == Node.TEXT_NODE:
                    ptext += n1.nodeValue
                else:
                    for n2 in n1.childNodes:
                        if n2.nodeType == Node.TEXT_NODE:
                            ptext += n2.nodeValue
            #self.paragraphs.append([parent_tag, ptext])
            if grandparent_tag == 'abstract':
                self.abstract.append([parent_tag, ptext])
            elif grandparent_tag == 'body':
                self.paragraphs.append([parent_tag, ptext])

    def xml2txt(self):
        #print len(self.title), len(self.abstract), len(self.body)
        #if self.title: print self.title
        fh = codecs.open(self.outfile, 'w', encoding='utf8')
        if self.title: fh.write(u"FH_TITLE:\n%s\n" % self.title)
        if self.journal: fh.write(u"FH_JOURNAL:\n%s\n" % self.journal)
        if self.subject: fh.write(u"FH_SUBJECT:\n%s\n" % self.subject)
        if self.year: fh.write(u"FH_DATE:\n%s\n" % self.year)
        if self.abstract:
            fh.write(u"FH_ABSTRACT:\n")
            for para in self.abstract:
                if para[0] == 'sec': fh.write("%s\n" % para[1])
        if self.paragraphs:
            fh.write(u"FH_BODY:\n")
            for para in self.paragraphs:
                if para[0] == 'sec': fh.write("%s\n" % para[1])

    def save_to_file(self, output_directory):
        output_file = os.path.basename(self.fname)
        output_file = os.path.splitext(output_file)[0] + '.txt'
        fh = open(os.path.join(output_directory, output_file), 'w')
        self.save_to_fh(fh)

    def save_to_fh(self, fh):
        fh.write("SOURCE\t%s\n" % self.fname)
        fh.write("TITLE\t%s\n" % normalize(self.title))
        fh.write("YEAR\t%s\n" % self.year)
        count = 0
        for (parent, text, tokenized_text) in self.paragraphs:
            count += 1
            for sentence in [s for s in tokenized_text.split("\n") if s]:
                sentence = normalize(sentence)
                fh.write("P%d\t%s\t%s\n" % (count, parent.upper(), sentence))

    def pp(self, verbose=False):
        print "\n\n>>> %s\n%s\n" % (self.fname, '-' * 80)
        print "YEAR:\t%s" % self.year
        print "TITLE\t%s\n" % normalize(self.title)
        if verbose:
            count = 0
            for (parent, text, tokenized_text) in self.paragraphs:
                count += 1
                for sentence in [s for s in tokenized_text.split("\n") if s]:
                    sentence = normalize(sentence)
