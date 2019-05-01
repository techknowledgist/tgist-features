import codecs
from exceptions import UserWarning


class Section(object):
    """
    Represents a semantically-typed section in a document. Should be used by all
    SectionFactories because the code to write to the output uses this
    class. The section does not include the header, but self.header does contain
    the string of the header, if there is one. """

    SECTION_ID = 0
    
    def __init__(self):
        Section.SECTION_ID += 1
        self.id = Section.SECTION_ID
        self.parent_id = None
        self.types = []
        self.header = ""
        self.subsumers = []
        self.subsumer_types = set()
        self.subsumed = []
        self.filename = ""
        self.start_index = -1
        self.end_index = -1
        self.text = ""
        self.tag = None
        
    def __str__(self):
        (p1, p2) = (self.start_index, self.end_index)
        offsets = "id=%d pid=%s start=%d end=%d" % (self.id, self.parent_id, p1, p2)
        types = "types='%s'" % '|'.join(self.types)
        header = " header='%s'" % self.header if self.header else ''
        tagname = 'nil' if self.tag is None else self.tag.name
        return "<%s %s %s%s>" % (tagname, offsets, types, header)  # + str(self.subsumers)
    
    def __len__(self):
        return self.end_index - self.start_index

    def is_claim(self):
        return False

    def get_language(self):
        if self.tag is None:
            return None
        return self.tag.attr('lang', None)
        
    def set_parent_id(self):
        if self.subsumers:
            self.parent_id = self.subsumers[-1].id
            
    def is_header(self):
        return self.types == ['Header']

    def percolate_types(self, parent_types):
        if self.types == ['Header']:
            return
        print "\nPercolating", self
        print "   adding ", parent_types
        print "   to     ", self.types
        all_types = list(set(self.types + parent_types))
        self.types = all_types
        for sub in self.subsumed:
            sub.percolate_types(all_types)

    def pp(self):
        text_string = self.text.replace("\n", '\\n').encode('utf-8')[:80]
        (p1, p2) = (self.start_index, self.end_index)
        (BLUE, GREEN, END) = ('\033[34m', '\033[32m', '\033[0m')
        offsets = "%s<id=%d start=%d end=%d>%s" % (GREEN, self.id, p1, p2, END)
        types = "%s%s%s" % (BLUE, str(self.types), END)
        return "%s %s\n%s...\n" % (types, offsets, text_string)
    

class ClaimSection(Section):

    def __init__(self):
        Section.__init__(self)
        self.claim_number = -1
        self.parent_claims = []

    def is_claim(self):
        return True


class SectionFactory(object):
    """
    Abstract class that contains shared code for the section factories for all data
    types. Provides a unified interface for the code that calls the section creation
    code. The main method called by outside code is make_sections(), which should be
    implemented on all subclasses."""
    
    def __init__(self, text_file, fact_file, sect_file, fact_type, language, verbose=False):
        """
        The first two files are the ones that are given by the wrapper, the third is
        the file that the wrapper expects."""
        # reset the SECTION_ID class variable so that ids start at 1 for each file, this
        # is important because it makes the regression test much more robust.
        Section.SECTION_ID = 0
        self.language = language
        self.fact_type = fact_type
        self.text_file = text_file
        self.fact_file = fact_file
        self.sect_file = sect_file
        self.sections = []
        self.verbose = verbose

    def __str__(self):
        return "<%s on %s>" % (self.__class__.__name__, self.text_file[:-4])

    def make_sections(self):
        """
        Creates a list of Section instances in self.sections. Each subclass
        should implement this method. """        
        raise UserWarning, "make_sections() not implemented for %s " % self.__class__.__name__

    def section_string(self, section, suppress_empty=True):
        """
        Called by print_sections. Returns a human-readable string with relevant
        information about a particular section."""
        language = section.get_language()
        sec_string = "SECTION ID=%d" % section.id
        if section.parent_id is not None:
            sec_string += " PARENT_ID=%d" % section.parent_id
        if section.tag is not None:
            if section.tag.fact_type == 'BAE':
                sec_string += " STRUCT=\"" + section.tag.attributes.get('TYPE', 'None') + "\""
            else:
                sec_string += " STRUCT=\"" + section.tag.name + "\""
        if len(section.types) > 0:
            sec_string += " TYPE=\"" + "|".join(section.types).upper() + "\""
        if language is not None:
            sec_string += " LANGUAGE=\"%s\"" % language
        if len(section.header) > 0:
            # normalize whitespace to avoid having newlines in fact
            section_header = ' '.join(section.header.strip().split())
            sec_string += " TITLE=\"" + section_header + "\""
        if section.start_index is not -1:
            sec_string += " START=" + str(section.start_index)
        if section.end_index is not -1:
            sec_string += " END=" + str(section.end_index)
        try:
            if section.claim_number > 0:
                sec_string += " CLAIM_NUMBER=" + str(section.claim_number)
            if len(section.parent_claims) > 0:
                sec_string += " PARENT_CLAIMS=" + self.parent_claims_string(section.parent_claims)
        except AttributeError:
            pass   
        if self.verbose and len(section.text) > 0:
            if len(section.text) < 2000:
                sec_string += "\n"+section.text
            else:
                sec_string += "\n"+section.text[:900]+"  [...]  " + section.text[-900:]
        if suppress_empty and len(section.text.strip()) < 1:
            return None
        return sec_string + "\n"

    def parent_claims_string(self, parent_claims):
        ret_string = str(parent_claims[0])
        for claim in parent_claims[1:]:
            ret_string += ","
            ret_string += str(claim)
        return ret_string
    
    def print_sections(self, fh=None):
        """ Prints section data to a file handle or the sections file. """
        if fh is None:
            fh = codecs.open(self.sect_file, "w", encoding='utf-8')
        for section in self.sections:
            try:
                fh.write(self.section_string(section))
            except TypeError:
                pass
        fh.close()
        
    def print_hierarchy(self):
        print "Number of sections:", len(self.sections)
        for s in self.sections:
            if not s.subsumers:
                self.print_hierarchy_tree(s)

    def print_hierarchy_tree(self, section, indent=0):
        print "%s%s" % (' '*indent, section)
        for subsection in section.subsumed:
            self.print_hierarchy_tree(subsection, indent+3)

            
def section_gaps(sections, text, filename=""):
    """
    Finds the unlabeled sections in a text and labels them "Unlabeled". """
    
    gaps = []
    end = len(text)
    sections = sorted(sections, key=lambda x: x.start_index)
    covered = 0
    for section in sections:
        start_index = section.start_index
        end_index = section.end_index
        if start_index > covered:
            ul_section = Section()
            ul_section.types = ["Unlabeled"]
            ul_section.filename = filename
            ul_section.start_index = covered
            ul_section.end_index = start_index
            ul_section.text = text[covered:start_index]
            gaps.append(ul_section)
        if end_index > covered:
            covered = end_index
    if end > covered:
        ul_section = Section()
        ul_section.types = ["Unlabeled"]
        ul_section.filename = filename
        ul_section.start_index = covered
        ul_section.end_index = end
        ul_section.text = text[covered:end]
        gaps.append(ul_section)
    return gaps


def link_sections(sections):
    """ Links sections where one is subsuming the other. This does not quite build a tree,
    rather, for each section it creates a list of subsuming and subsumed sections. The
    subsumers list is ordered though so that the parent is always the last element."""
    for section in sections:
        for other_section in sections:
            if is_subsection(section, other_section):
                section.subsumers.append(other_section)
                for sem_type in other_section.types:
                    section.subsumer_types.add(sem_type)
                other_section.subsumed.append(section)
    # make sure that the subsumers are ordered so that the parent is always the last in
    # the list, this is also where the parent_id gets set
    for section in sections:
        section.subsumers.sort(key=lambda x: x.start_index)
        if section.subsumers:
            section.parent_id = section.subsumers[-1].id
            

def is_subsection(section, other_section):
    """ Returns true if the first section is included in the second."""
    if (other_section.start_index <= section.start_index
            and other_section.end_index >= section.end_index
            and len(other_section) > len(section)):
        return True


def make_section(text_file, tag, text, section_type=None):
    """Utility method to create a Section given a filename, a unicode string that contains
    the content of the document, an instance of readers.common.Tag and an optional section
    type."""
    if tag is None:
        return None
    section = ClaimSection() if section_type == 'Claim' else Section()
    if section_type is not None:
        section.types = [section_type]
    section.filename = text_file
    section.start_index = tag.start_index
    section.end_index = tag.end_index
    section.text = tag.text(text)
    section.tag = tag
    return section
