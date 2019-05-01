"""
*****GOALS*****

1. Recognize the claims section, as well as the numbered list of claims

 2. In addition, for each claim there needs to be a pointer to the parent claim.
 Many claims start with text like "The method of claim 9 wherein" or "The system
 of claim 1 wherein". There is probably a limited vocabulary here so it should
 not be hard to find these.

 3. Recognize (and type) example sections as well as sections "Field of
 Invention", "Background of Invention", "Summary", "Description". For some we
 already have types, for others we do not. This does bring up the question on
 whether we should have a distinction between general types and types for
 certain domains or section generator types. For now we do not need to worry
 here, but we should keep it in the back of our minds.

"""

from common import Tag, load_data
from common import tags_with_name, tags_with_type, tags_with_matching_type


def read_tags(text_file, fact_file, fact_type):
    """Returns the text as a unicode string as well as a dictionary with the various kinds
    of tags."""
    (text, tags) = load_data(text_file, fact_file, fact_type)
    if fact_type == 'BAE':
        structures = tags_with_name(tags, 'STRUCTURE')
        tag_dictionary = read_tags_bae(structures)
    else:
        tag_dictionary = read_tags_basic(tags)
    return (text, tag_dictionary)


def read_tags_bae(structures):

    def is_claim(text, claims_section):
        return text.attributes["TYPE"] == "TEXT" \
            and text.start_index >= claims_section.start_index \
            and text.end_index <= claims_section.end_index

    tags = {}
    tags['headers'] = tags_with_type(structures, 'SECTITLE')
    tags['paragraphs'] = tags_with_type(structures, 'TEXT')
    tags['abstracts'] =  tags_with_type(structures, 'ABSTRACT')
    tags['summaries'] = tags_with_type(structures, 'SUMMARY')
    tags['related_applications'] = tags_with_type(structures, 'RELATED_APPLICATIONS')
    tags['sections'] = tags_with_type(structures, 'TEXT_CHUNK')
    tags['claims_sections'] = tags_with_type(structures, 'CLAIMS')

    # move the paragraphs that are really claims
    if tags['claims_sections']:
        claims_section = tags['claims_sections'][0]
        paragraphs = []
        claims = []
        for p in tags['paragraphs']:
            if is_claim(p, claims_section):
                claims.append(p)
            else:
                paragraphs.append(p)
        tags['paragraphs'] = paragraphs
        tags['claims'] = claims
    else:
        tags['claims'] = []

    # TODO: with this, we basically restore the original tags, this is potentilly rather
    # brittle though and I should think of a better way to do this
    for t in tags['abstracts']: t.name = 'abstract'
    for t in tags['headers']: t.name = 'heading'
    for t in tags['paragraphs']: t.name = 'p'
    for t in tags['summaries']: t.name = 'summary'
    for t in tags['sections']: t.name = 'description'
    for t in tags['claims_sections']: t.name = 'claims'
    for t in tags['claims']: t.name = 'claim'
    for t in tags['related_applications']: t.name = 'related-apps'
    #for t in tags['']: t.name = ''

    return tags


def read_tags_basic(taglist):

    tags = {}

    # the following are used in English patents, and many of them also in chinese and
    # german patents
    tags['meta_tags'] = meta_tags(taglist)
    taglist = [t for t in taglist if t.name != 'date']
    tags['headers'] = tags_with_name(taglist, 'heading')
    tags['paragraphs'] = tags_with_name(taglist, 'fs:P')
    tags['abstracts'] =  tags_with_name(taglist, 'fs:AbstractBlock')
    tags['summaries'] = tags_with_name(taglist, 'summary')
    tags['related_applications'] = tags_with_name(taglist, 'related-apps')
    tags['sections'] = tags_with_name(taglist, 'description')
    tags['claims_sections'] = tags_with_name(taglist, 'claims')
    tags['claims'] = tags_with_name(taglist, 'claim')
    tags['claims'] = sorted(tags['claims'], key = lambda x: x.start_index)

    #for t in tags['abstracts']: print t

    return tags


def meta_tags(taglist):
    p1, p2 = 0, 0
    metatags = []
    for t in taglist:
        if t.name == 'invention-title':
            metatags.append(t)
        if t.name == 'publication-reference':
            metatags.append(t)
            p1, p2 = t.start_index, t.end_index
        if t.name == 'date':
           if t.is_contained_in(p1, p2):
               metatags.append(t)
    return metatags
