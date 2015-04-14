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
WOS_ITEM = {}

parsing = False
in_abstract = False

def print_item(fh):
    fh.write("\nui: %s\n" % WOS_ITEM['ui'])
    fh.write("title: %s\n" % WOS_ITEM['title'])
    fh.write("subject: %s\n" % WOS_ITEM['subject'])
    if WOS_ITEM.get('abstract') is not None:
        fh.write("\n%s" % WOS_ITEM['abstract'])
    fh.write("\n")
        
subjects = open("out-subjects-%s.txt" % ARCHIVE, 'w')
duplicates = open("out-duplicates-%s.txt" % ARCHIVE, 'w')

for line in fh:
    if line.startswith('<REC>'):
        WOS_ITEM = {}
        parsing = False
        RECS += 1
    elif line.startswith('<ui>'):
        ui = line.split('>')[1].split('<')[0]
        #if line.startswith('<ui>'+DUPLICATE_UI):
        if DUPLICATE_UIS.get(ui) is not None:
            parsing = True
        if parsing: WOS_ITEM['ui'] = ui
    elif line.startswith('<subject '):
        subject = line.split('>')[1].split('<')[0]
        SUBJECTS[subject] = SUBJECTS.get(subject, 0) + 1
        if parsing: WOS_ITEM['subject'] = subject
    elif line.startswith('<item_title>'):
        title = line.split('>')[1].split('<')[0]
        if parsing: WOS_ITEM['title'] = title
    elif line.startswith('<abstract avail="Y"'):
        in_abstract = True
        ABSTRACTS += 1
    elif line.startswith('</abstract>'):
        in_abstract = False
    elif line.startswith('</REC>'):
        if parsing: print_item(duplicates)
    else:
        if parsing and in_abstract:
            WOS_ITEM['abstract'] = WOS_ITEM.get('abstract','')+line

for subj, count in SUBJECTS.items():
    subjects.write("%d\t%s\n" % (count, subj))

print "Done"
print "RECS:", RECS
print "Abstracts:", ABSTRACTS
