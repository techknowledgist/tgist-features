"""

Create an index on WoS archives

Like index.py, but now for the 2014 format.

"""

# TODO. This script makes the incorrect assumption that each record has only one
# subject. This needs to be fixed and then this step, and probably all or most
# below, will need to be redone.


import sys, os, gzip, codecs, time

WOS_DIR = '/home/j/corpuswork/fuse/FUSEData/2013-04/WoS_2014_Aug'


def read_domains():
    domains = {}
    for line in open('domains.txt'):
        line = line.strip()
        if not line: continue
        if line[0] == '#': continue
        if line.startswith('DOMAIN'):
            prefix, domain_code, domain_name = line.split("\t")
        else:
            journal, issns = line.split("\t")
            for issn in issns.split():
                issn = issn[:4] + '-' + issn[4:]
                domains[issn] = domain_code
    return domains


class WOSItem(object):

    def __init__(self):
        self.fields = {}

    def add(self, item, line):
        item_value = line.split('>')[1].split('<')[0]
        self.fields[item] = item_value
        return item_value

    def add_value(self, item, line):
        item_value = line.split('value="')[1].split('"')[0]
        self.fields[item] = item_value
        return item_value

    def add_line(self, field, line):
        self.fields['abstract'] = self.fields.get('abstract','') + line

    def set_domain(self):
        self.fields['domain'] = DOMAINS.get(self.fields.get('issn'), 'nil')

    def write(self, fh):
        fh.write("\n")
        for field in ['ui', 'ut', 'item_title', 'issue_title', 'issn', 'subject']:
            fh.write("%s: %s\n" % (field, self.fields.get(field)))
        if self.fields.get('abstract') is not None:
            fh.write("\n%s" % self.fields['abstract'])
        fh.write("\n")

    def write_index_line(self, fh1, fh2):
        fh1.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n" %
                  (self.fields.get('ut'), self.fields.get('ui'),
                   self.fields.get('domain'), self.fields.get('issn'),
                   len(self.fields.get('abstract','')),
                   self.fields.get('subject'),
                   self.fields.get('issue_title')))
        fh2.write("%s\t%s\n" %
                  (self.fields.get('ut'), self.fields.get('item_title')))



def index_archive(archive):

    RECS = 0
    ABSTRACTS = 0

    gzipfile = gzip.open(os.path.join(WOS_DIR, archive), 'rb')
    fh = codecs.getreader('utf-8')(gzipfile)
    index = open("out/index-main-%s.txt" % ARCHIVE[:-3], 'w')
    index_titles = open("out/index-titles-%s.txt" % ARCHIVE[:-3], 'w')

    t0 = time.time()
    in_abstract = False

    print "%s..." % archive,
    sys.stdout.flush()
    
    for line in fh:
        #if RECS > 50: break
        if line.startswith('<REC '):
            wos = WOSItem()
            RECS += 1
            in_abstract = False
        elif line.startswith('<UID>'):
            wos.add('ut', line)
            wos.add('ui', line)
        # this is wrong, there can be more than one subject
        # staying consistent with index.py, which has the same issue
        elif line.startswith('<subject ascatype="traditional"'):
            wos.add('subject', line)
        elif line.startswith('<title type="item">'):
            wos.add('item_title', line)
        elif line.startswith('<title type="source">'):
            wos.add('issue_title', line)
        elif line.startswith('<identifier type="issn" '):
            wos.add_value('issn', line)
            wos.set_domain()
        elif line.startswith('<abstract_text'):
            in_abstract = True
            ABSTRACTS += 1
        elif line.startswith('</abstract_text>'):
            in_abstract = False
        elif line.startswith('</REC>'):
            #wos.write(sys.stdout)
            wos.write_index_line(index, index_titles)
        else:
            if in_abstract:
                wos.add_line('abstract', line)

    print "%d records and %s abstracts, %d seconds" \
          % (RECS, ABSTRACTS, time.time() - t0)


if __name__ == '__main__':

    DOMAINS = read_domains()
    ARCHIVE = 'WR_2013_20140820152426_PSHU_0001.xml.gz'
    if len(sys.argv) > 1:
        ARCHIVE = sys.argv[1]
    index_archive(ARCHIVE)
