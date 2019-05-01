import codecs

# List of interesting tags. This list is just for patents and CNKI
# documents. Now all tags are handed in to the document parser.

# Should these be restricted to just the ones for the collections? Another
# question to answer is whether we should restrict the tags at all. And should
# this be a utility in utils because it is so collection-dependent?

PATENT_TAGS = (
    'description', 'abstract', 'technical-field', 'background-art',
    'related-apps', 'claims', 'claim', 'p', 'heading', 'summary',
    'invention-title', 'publication-reference', 'date')

CNKI_TAGS = (
    'fs:Body', 'fs:BodySection', 'fs:P', 'fs:Stuff',
    'fs:AbstractBlock', 'fs:Title', 'fs:ArticleTitle',
    'fs:AuthorBlock', 'fs:Reference')

TAGS = PATENT_TAGS + CNKI_TAGS


def transform_tags_file(infile, outfile):
    """Takes an xml file as created by the xslt scripts in standoff and create a file that is
    more like the BAE fact file, using just the tags that are of interest."""

    out = codecs.open(outfile, 'w', encoding='utf-8')
    for line in codecs.open(infile, encoding='utf-8'):
        fields = line.strip().split()
        tag = fields[0][1:]
        if tag in TAGS:
            tagline =  tag + ' ' + ' '.join(fields[1:])
            tagline = tagline.strip('/>')
            out.write(tagline+"\n")
