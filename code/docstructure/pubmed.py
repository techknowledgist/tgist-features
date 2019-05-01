
"""

Module with code to create sections for Pubmed data. 

"""


import normheader
import readers.pubmed
from sections import Section, SectionFactory, section_gaps, link_sections


class BiomedNxmlSectionFactory(SectionFactory):

    def make_sections(self):
        """
        Given a list of headertag/sectiontag pairs, a list of abstract tags, and the raw
        text of the article, converts them into a list of semantically typed sections."""

        (a_text, a_tags) = readers.pubmed.load_data(self.text_file, self.fact_file)
        raw_sections = readers.pubmed.headed_sections(a_tags, separate_headers=True)
        text_sections = filter(lambda x: type(x) == tuple, raw_sections)
        header_sections = filter(lambda x: type(x) != tuple, raw_sections)
        abstracts = readers.pubmed.find_abstracts(a_tags)
        
        for header, sect in text_sections:
            section = Section()
            section.types = normheader.header_to_types(header.text(a_text))
            section.header = header.text(a_text)
            section.filename = self.text_file
            section.start_index = sect.start_index
            section.end_index = sect.end_index
            section.text = sect.text(a_text)
            self.sections.append(section)

        for header in header_sections:
            section = Section()
            section.types = ["Header"]
            section.filename = self.text_file
            section.start_index = header.start_index
            section.end_index = header.end_index
            section.text = header.text(a_text)
            self.sections.append(section)

        for abstract in abstracts:
            section = Section()
            section.types = ["Abstract"]
            section.filename = self.text_file
            section.start_index = abstract.start_index
            section.end_index = abstract.end_index
            section.text = abstract.text(a_text)
            self.sections.append(section)
            
        self.sections.extend(section_gaps(self.sections, a_text, self.text_file))
        link_sections(self.sections)
        self.sections = sorted(self.sections, key= lambda x: x.start_index)
