import sys, re

import normheader
from readers.cnki import read_tags
from sections import SectionFactory, make_section


# Used to detect paragraphs that are headers. Will probably overgeneralize if we are not
# careful. For example, any paragraph that has 'background art' in it will now be a
# heading. Limit header paragraphs to a maximum size.
HEADER_PARAGRAPHS = (
    'summary',
    'summary of invention',
    'summary of the invention',
    'background',
    'background of invention',
    'background of the invention',
    'background art',
    'description of prior art',
    'description of related art',
    'field',
    'field of invention',
    'field of the invention')

# Mapping from structural tags to basic section types. Possibly belongs in normheader.
TAGNAME_TO_TYPE_MAPPINGS = {
    'date': ['Meta-Date'],
    'invention-title': ['Meta-Title'],
    'abstract': ['Abstract'],
    'description': ['Description'],
    'related-apps': ['Related_Applications'],
    'summary': ['Summary'],
    'heading': ['Header'],
    'claims': ['Claims'],
    'claim': ['Claim'] }


def sorted_tags_from_dictionary(tag_dict):
    """Return a sorted list of all tags in a dictionary, where the keys in the dictionary
    are lists of Tags. Sorting is accoring to the begin and end offsets of the tags."""
    all_tags = []
    for tag_group in tag_dict.keys():
        for tag in tag_dict[tag_group]:
            all_tags.append(tag)
    all_tags.sort()  # necessary for the insertion procedure
    return all_tags

def print_tag_list(tags, fname):
    fh = open(fname, 'w')
    for t in tags:
        fh.write("%s\n" % t)


class SectionTree(object):

    """In a SectionTree, each child's offsets are (i) embedded in the offset of the
    parent, (ii) precede the offsets of its reight sibling and (iii) follow the offsets of
    its left sibling."""

    def __init__(self, tags, text=''):
        """Initialize the tree given the unicode string for th enetire document and the
        dictionary of tags."""
        self.root = TopNode(self)
        self.text = text
        self.idx = {}
        # sorting is necessary for the insertion procedure
        sorted_tags = sorted_tags_from_dictionary(tags)
        #print_tag_list(sorted_tags, 'ws-tags.txt')
        for tag in sorted_tags:
            self.insert(tag)
        self.sort()

    def nodes(self):
        return self.root.nodes()

    def claims(self):
        return [n for n in self.nodes() if n.name == 'claim']

    def insert(self, tag):
        new_node = Node(tag, self)
        self.root.insert(new_node)

    def sort(self):
        self.root.sort()

    def find_headers(self):
        """Find those paragraphs that are headers and change their name."""
        self.root.find_headers()

    def add_types(self):
        """Add type derived from inherent type of a tag."""
        self.root.add_types([])
        self.copy_header_types()

    def copy_header_types(self):
        """Copy semantic type of a header to siblings to the right. Only adds to p tags
        and does not percolate down on those tags. Assumes that this is about headers
        where there is no further structure down below."""
        # TODO: this effectively copies the behaviour of the old code, but it does not
        # deal with embedded headers. If for example you have two consecutive paragraphs
        # where the first is 'BACKGROUND OF THE INVENTION' and the very next is '1. Field
        # of the Invention', then any types derived from the first will be blocked by the
        # second.
        nodes = self.nodes()
        for i in range(len(nodes)):
            node = nodes[i]
            if node.is_header():
                header_types = normheader.header_to_types(node.text())
                #header_types = [t for t in header_types if t != 'Other']
                if not header_types:
                    continue
                node.add_header_types(header_types)
                for j in range(i + 1, len(nodes)):
                    next = nodes[j]
                    if next.is_header(): break
                    if next.name == 'claims': break
                    next.add_header_types(header_types)

    def pp(self):
        self.root.pp()

    def pp_nodes(self):
        for n in self.nodes():
            print n.tag

    def pp_index(self):
        for tagname, nodes in self.idx.items():
            print tagname
            for node in nodes:
                print '  ', node


class Node(object):

    INDENT_STEP = '   '

    def __init__(self, tag, tree=None):
        self.p1 = tag.start_index
        self.p2 = tag.end_index
        #self.name = tag.get_type() if tag.fact_type == 'BAE' else tag.name
        self.name = tag.name
        self.types = []
        self.tag = tag
        self.children = []
        self.tree = tree

    def __str__(self):
        text = self.tree.text[self.p1:self.p2].replace("\n", ' ').strip()
        if self.name == 'heading':
            text = ' ===== ' + text + ' ====='
        elif self.name in ('p', 'claim'):
            text = ' "' + text[:70] + '..."'
        else:
            text = ''
        return "%d-%d %s %s%s" % (self.p1, self.p2, self.name, self.types, text)

    def __cmp__(self, other):
        return cmp(self.p1, other.p1)

    def text(self):
        return self.tree.text[self.p1:self.p2]

    def nodes(self, collected_nodes):
        for n in self.children:
            collected_nodes.append(n)
            n.nodes(collected_nodes)

    def is_header(self):
        return self.name == 'heading'

    def contains(self, node):
        """Return True if self contains the other node."""
        return self.p1 <= node.p1 and self.p2 >= node.p2

    def get_children_contained_by_node(self, other_node):
        """Return a ist of indexes in self.children with all children that are contained
        in other_node."""
        idx = -1
        contained_nodes = []
        for node in self.children:
            idx += 1
            if other_node.contains(node):
                contained_nodes.append(idx)
        return contained_nodes

    def insert(self, new_node):
        """Insert a new node into self, this assumes that self contains the new node (that
        is, it starts before and ends after the new node."""
        # hand it to a child node if that child contains the new node
        for node in self.children:
            if node.contains(new_node):
                node.insert(new_node)
                return
        # some children are contained by the new_node, do a flip; this is for now
        # effectively disabled beacuse it is not needed, code is left here in case it
        # comes in handy
        contained_nodes = self.get_children_contained_by_node(new_node)
        if contained_nodes and False:
            self.flip(new_node, contained_nodes)
            return
        # in other cases, just append it
        self.children.append(new_node)

    def flip(self, new_node, contained_nodes):
        i1 = contained_nodes[0]
        i2 = contained_nodes[-1]
        new_node.children = self.children[i1:i2+1]
        self.children[i1:i2+1] = [new_node]

    def sort(self):
        self.children.sort()
        for n in self.children:
            n.sort()

    def find_headers(self):
        """Find all paragraphs that are actually headers and change their name from p into
        heading."""
        for node in self.children:
            if node.name == 'p':
                if text_is_header(node.text()):
                    node.name = 'heading'
            node.find_headers()

    def add_types(self, type_list):
        """Retrieve the type inherent to the tag name, add it to the list handed in from
        the parent, assign the new list as the type of self, and hand the new list down to
        the children."""
        type_list = type_list + TAGNAME_TO_TYPE_MAPPINGS.get(self.name, [])
        self.types = type_list
        for n in self.children:
            n.add_types(type_list)

    def add_header_types(self, header_types):
        """Add types inherited from a sibling header, but only if it does not add
        redundant type information."""
        closest_type = self.types[-1] if self.types else None
        for ht in header_types:
            if closest_type != ht:
                self.types.append(ht)

    def pp(self, indent=0):
        self.pp_default(indent)

    def pp_default(self, indent=0):
        print "%s%s" % (indent * Node.INDENT_STEP, self)
        for n in self.children:
            n.pp(indent + 1)

    def pp_with_attributes(self, indent=0):
        attrs = ''
        if self.tag is not None:
            attrs = " {%s}" % ', '.join(["%s=%s" % (a,v)
                                         for (a,v) in self.tag.attributes.items()
                                         if a not in ('standoff:length', 'standoff:offset')])
        print "%s<%s %d %d> %s" % (indent * Node.INDENT_STEP, self.name, self.p1, self.p2, attrs)


class TopNode(Node):

    def __init__(self, tree=None):
        self.p1 = 0
        self.p2 = sys.maxint
        self.name = 'root'
        self.types = []
        self.tag = None
        self.children = []
        self.tree = tree

    def nodes(self):
        collected_nodes = []
        for n in self.children:
            collected_nodes.append(n)
            n.nodes(collected_nodes)
        return collected_nodes




class CnkiSectionFactory(SectionFactory):

    def make_sections(self, separate_headers=True):
        """Read the text and the tags and create a list of sections. First creates a
        SectionTree and adds types to this tree, then populates the sections instance
        variable from this tree. Then adds claim numbers and parent claim numbers to the
        claim sections."""

        # build the section tree
        (text, tags) = read_tags(self.text_file, self.fact_file, self.fact_type)
        section_tree = SectionTree(tags, text)
        #section_tree.pp()
        section_tree.find_headers()
        section_tree.add_types()
        #print_tags(text, tags)
        
        # populate the sections variable from the section tree
        for node in section_tree.nodes():
            section_type = TAGNAME_TO_TYPE_MAPPINGS.get(node.name, ['Other'])[0]
            new_section = make_section(self.text_file, node.tag, text, section_type)
            new_section.types = node.types
            self.sections.append(new_section)

        # find parent claims
        claims = [s for s in self.sections if s.is_claim()]
        claim_index = 0
        for claim in claims:
            claim_index += 1
            claim.claim_number = claim_index
            claim_refs = re.findall(r"claim \d+", claim.text)
            for ref in claim_refs:
                claim_id = int(ref.split()[-1])
                claim.parent_claims.append(claim_id)


def text_is_header(text):
    """Return True if text is likely to be a header, which is the case if it is below a
    certain size and contains a string indicative of headers. Should probably use a
    similar approach as for the simple Elsevier documents."""
    text = ' '.join(text.strip().lower().split())
    for header in HEADER_PARAGRAPHS:
        if len(text) < 50 and text.find(header) > -1:
            return True
    return False


def print_tags(text, tags):
    for name, l in tags.items():
        print name
        for t in l:
            # somehow the former caused problems for the default standoff data
            title = "['%s']" % text[t.start_index-1:t.end_index] if name == 'headers' else ''
            title = text[t.start_index:t.end_index] if name == 'headers' else ''
            print "   %s %s" % (t, title)
