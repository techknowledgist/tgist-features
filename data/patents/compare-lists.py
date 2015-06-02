"""

Finds the overlap between the documents in the 2013 LNCN data drop and those in
the 2014 LNCN data drop.

Here is what we get when we run this (takes about a minute):

    Read 5122175 lines from 2013 from ln_cn.all.ordered.txt
    Read 2070042 lines from 2014 from ln-cn-updates-2014-09-23-sorted.txt

    2013 unique lines 5122175
    2014 unique lines 1342010

    BOTH 198697
    EITHER 6265488
    ONLY_2013 4923478
    ONLY_2014 1143313

    Printing out-compare-only-2014.txt...

The file printed has all paths to files that do not occur in the 2013 data drop
(with 'not occurring' meaning that there is no file with the same base name).

The file out-compare-only-2014.txt has a list of paths from them, with the paths
pointing to eldrad locations.

Note the large number of 'duplicates' in the 2014 data. I tracked a few of those
and in all cases these are small changes in the meta data.

"""


import os

LISTS = '/home/j/corpuswork/fuse/FUSEData/lists'

LIST_2013 = os.path.join(LISTS, 'ln_cn.all.ordered.txt')
LIST_2014 = os.path.join(LISTS, 'ln-cn-updates-2014-09-23-sorted.txt')


DOCS_2013 = {}
DOCS_2014 = {}

count = 0
for line in open(LIST_2013):
    count += 1
    if count > 100000: break
    base = os.path.basename(line.split()[1])
    DOCS_2013[base] = True
print "Read %s lines from 2013 from" % count, os.path.basename(LIST_2013)

dups = open('out-compare-dups-2014.txt', 'w')
count = 0
for line in open(LIST_2014):
    count += 1
    if count > 100000: break
    base = os.path.basename(line.strip())
    if DOCS_2014.has_key(base):
        dups.write(base+"\n")
    DOCS_2014[base] = line.strip()
print "Read %s lines from 2014 from" % count, os.path.basename(LIST_2014)

print
print '2013 unique lines', len(DOCS_2013)
print '2014 unique lines', len(DOCS_2014)

ONLY_2013 = {}
ONLY_2014 = {}
BOTH = {}
EITHER = {}

for id in DOCS_2013.keys():
    EITHER[id] = True
    if DOCS_2014.has_key(id):
        BOTH[id] = True
    else:
        ONLY_2013[id] = True

for id, path in DOCS_2014.items():
    EITHER[id] = True
    if DOCS_2013.has_key(id):
        BOTH[id] = True
    else:
        ONLY_2014[id] = path

print
print 'BOTH', len(BOTH)
print 'EITHER', len(EITHER)
print 'ONLY_2013', len(ONLY_2013)
print 'ONLY_2014', len(ONLY_2014)

print "\nPrinting out-compare-only-2014.txt..."
fh = open('out-compare-only-2014.txt', 'w')
for path in sorted(ONLY_2014.values()):
    fh.write(path+"\n")
