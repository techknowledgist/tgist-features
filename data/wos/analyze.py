"""

Some analytics on a WoS archive.

Prints:
    - a file with all subjects
    - a file with some infor on two duplicate ui tags from WoS.out.2012000044.gz
    - number of REC tags and number of non-empty abstracts

For WoS.out.2012000044.gz, we get 1042 REC tags and 966 non-empty abstracts.

"""


import sys, os, gzip, codecs

WOS_DIR = '/home/j/corpuswork/fuse/FUSEData/2013-04/WoS_2012_Aug'
ARCHIVE = 'WoS.out.2012000044.gz'
FNAME = os.path.join(WOS_DIR, ARCHIVE)

DUPLICATE_UIS = {'0003059653': True, '0003022535': True}

gzipfile = gzip.open(FNAME, 'rb')
fh = codecs.getreader('utf-8')(gzipfile)

RECS = 0
ABSTRACTS = 0

SUBJECTS = {}
ISSUE_TITLES = {}

# Science
# Nature
# Proceedings of the National Academy of Science (PNAS)
A01 = ['0036-8075', '0028-0836', '0027-8424']


def read_domains():
    domains = {}
    for line in open('domains.txt'):
        line = line.strip()
        if not line: continue
        if line[0] == '#': continue
        if line.startswith('DOMAIN'):
            prefix, domain_code, domain_name = line.split("\t")
            print domain_code, domain_name
        else:
            journal, issns = line.split("\t")
            for issn in issns.split():
                print '  ', issn, domain_code


class WOSItem(object):

    def __init__(self):
        self.fields = {}
        
    def add(self, item, line):
        item_value = line.split('>')[1].split('<')[0]
        self.fields[item] = item_value
        return item_value

    def add_line(self, field, line):
        self.fields['abstract'] = self.fields.get('abstract','') + line

    def write(self, fh):
        fh.write("\n")
        for field in ['ui', 'ut', 'item_title', 'issue_title', 'issn', 'subject']:
            fh.write("%s: %s\n" % (field, self.fields.get(field)))
        if self.fields.get('abstract') is not None:
            fh.write("\n%s" % self.fields['abstract'])
        fh.write("\n")

read_domains()
exit()
    
index = open("out-subjects-%s.txt" % ARCHIVE, 'w')
subjects = open("out-subjects-%s.txt" % ARCHIVE, 'w')
issue_titles = open("out-issue-titles-%s.txt" % ARCHIVE, 'w')
duplicates = open("out-duplicates-%s.txt" % ARCHIVE, 'w')
domain_a01 = open("out-domain-A01-%s.txt" % ARCHIVE, 'w')
domain_a01b = open("out-domain-A01b-%s.txt" % ARCHIVE, 'w')

in_abstract = False
p_duplicates = False
p_A01 = False

for line in fh:
    if line.startswith('<REC>'):
        wos = WOSItem()
        p_A01 = False
        p_duplicates = False
        RECS += 1
    elif line.startswith('<ut>'):
        wos.add('ut', line)
    elif line.startswith('<ui>'):
        ui = wos.add('ui', line)
        if DUPLICATE_UIS.get(ui) is not None:
            p_duplicates = True
    elif line.startswith('<subject '):
        subject = wos.add('subject', line)
        SUBJECTS[subject] = SUBJECTS.get(subject, 0) + 1
    elif line.startswith('<item_title>'):
        wos.add('item_title', line)
    elif line.startswith('<issue_title>'):
        title = wos.add('issue_title', line)
        ISSUE_TITLES[title] = ISSUE_TITLES.get(title, 0) + 1
    elif line.startswith('<issn>'):
        issn = wos.add('issn', line)
        if issn in A01:
            parsing = True
            p_A01 = True
    elif line.startswith('<abstract avail="Y"'):
        in_abstract = True
        ABSTRACTS += 1
    elif line.startswith('</abstract>'):
        in_abstract = False
    elif line.startswith('</REC>'):
        if p_duplicates: wos.write(duplicates)
        if p_A01:
            wos.write(domain_a01b)
    else:
        if in_abstract:
            wos.add_line('abstract', line)
            
for subj, count in SUBJECTS.items():
    subjects.write("%d\t%s\n" % (count, subj))

for title, count in ISSUE_TITLES.items():
    issue_titles.write("%d\t%s\n" % (count, title))

print "Done"
print "RECS:", RECS
print "Abstracts:", ABSTRACTS
