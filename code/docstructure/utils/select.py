"""

Module that gives access to individual sections in a file that was processed by the
document structure parser.

Usage:

   % python select.py elsevier-simple.txt elsevier-simple.sect INTRODUCTION

   this selects all sections whose type is INTRODUCTION
   
   Note that different types can refer to the same stretch of text.

Call this from other scripts as follows:

   >>> reader = SectionReader(text_file, sect_file)
   >>> reader.get_sections(section_type='RELATED_APPLICATIONS')
   >>> reader.get_sections(struct='p')
   >>> reader.get_sections(section_type='RELATED_APPLICATIONS', struct='p')

In the first form, you will get all sections where one of the section types is
'RELATED_APPLICATIONS'. In the second form, you get all sections with the structural tag
'p'. This works currently only well for the BASIC tag type (and not the BAE tag type,
which is always STRUCTURE, but we should take the type there, for example CLAIMS or
TEXT). In the third form, you get the intersection of those two.

The main limitation is that this script does not take embedding into consideration. So a
section is basically defined as a stretch of text between two headers. This is due to
current limitations on what the document parser produces.

"""


import sys, codecs


class Section(object):

    def __init__(self, line, text):
        fields = line.strip().split()
        self.tag = fields[0]
        self.id = None
        self.language = None
        self.start = -1
        self.end = -1
        self.types = [None]
        self.types = []
        self.struct = None
        self.claim_number = None
        self.parent_claims = []
        self._read_attributes(fields)
        self.text = text[self.start:self.end]

    def _read_attributes(self, fields):
        attrs = [field.split('=') for field in fields[1:] if len(field.split('=')) == 2]
        for a,v in attrs:
            v = v.strip('"')
            if a == 'ID': self.id = v
            elif a == 'START': self.start = int(v)
            elif a == 'END': self.end = int(v)
            elif a == 'LANGUAGE': self.language = v
            elif a == 'TYPE': self.types = v.split('|')
            elif a == 'STRUCT': self.struct = v
            elif a == 'CLAIM_NUMBER': self.claim_number = int(v)
            elif a == 'PARENT_CLAIMS': self.parent_claims = [int(c) for c in v.split(',')]
            else:
                print "WARNING: unknown feature pair:", a, v

    def __str__(self):
        types = '|'.join(self.types) if self.types else 'None'
        return "<SECTION id=%s %d-%d struct=%s types=[%s]>" % \
            (self.id, self.start, self.end, self.struct, types)


class SectionReader(object):

    """Object that stores the text and, for each section struct and section type, a list
    of sections. It maintains these object to give easy access to the content of all
    sections in a document."""
    
    def __init__(self, text_file, sect_file):
        """Load the text and the section types."""
        self.text = codecs.open(text_file, encoding='utf-8').read()
        self.struct2sections = {}
        self.type2sections = {}
        fh_sect = codecs.open(sect_file, encoding='utf-8')
        for line in fh_sect:
            section = Section(line, self.text)
            self.struct2sections.setdefault(section.struct, []).append(section)
            for section_type in section.types:
                self.type2sections.setdefault(section_type, []).append(section)

    def get_sections(self, section_type=None, struct=None):
        """Return a list of section with the given section type and/or struct."""
        if section_type is not None and struct is not None:
            l1 = self.type2sections.get(section_type, [])
            l2 = self.struct2sections.get(struct, [])
            return list(set(l1) & set(l2))
        if section_type is not None:
            return self.type2sections.get(section_type, [])
        if struct is not None:
            return self.struct2sections.get(struct, [])
        return []

    def section_types(self):
        """Return a list of all section types in the document."""
        return sorted(self.type2sections.keys())

    def section_structs(self):
        """Return a list of all section structs in the document."""
        return sorted(self.struct2sections.keys())



if __name__ == '__main__':

    text_file, sect_file, sectiontype = sys.argv[1:4]
    reader = SectionReader(text_file, sect_file)
    for section in reader.get_sections(sectiontype='CLAIM'):
        print section
        print section.text
