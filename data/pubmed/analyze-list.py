"""

Some analytics on 

/home/j/corpuswork/fuse/FUSEData/lists/nxml-files-random.txt

Usage:

    python analyze-list.py

Most important outcomes:

    - the filename is not unique, there are 9 exceptions; the combination of
      first letter, journal name and file name is also not unique in the very
      same way

    - the combination of the meaningful part of the path (the hexadecimal) plus
      the filename is unique.
      
    - there are 2083 different journals
    
For short paths, there are several options: (1) use the first hexadecimal, for
all of pubmed, there will never more than about 1000 files in one of those
subdirectories, (2) use the journal name. The latter will result in many
top-level directories, but we could deal with that by using the first letter
as the first path element, however, we would have to deal with the duplicates.

However, using

"""

import os, copy

LISTDIR = '/home/j/corpuswork/fuse/FUSEData/lists'
LISTFILE = LISTDIR + os.sep + 'nxml-files-random.txt'

lines = 0
files = {}
paths = {}
journals_by_letter = {}
duplicates = []

for line in open(LISTFILE):
    lines += 1
    path_elements = line.strip().split(os.sep)
    hex1 = path_elements[2]
    hex2 = path_elements[3]
    journal = path_elements[4].rstrip("_-1234567890")
    first = journal[0].lower()
    fname = path_elements[-1]
    if files.has_key(fname):
        print fname
        #print copy.copy(files[fname])
        duplicates.append((copy.deepcopy(files[fname]), path_elements))
        files[fname].append(path_elements)
    else:
        files[fname] = path_elements
    journals_by_letter.setdefault(first,{})[journal] = True
    #journals_by_letter[first] = journals_by_letter.get(first,0) + 1
    minipath = "%s/%s/%s" % (hex1, hex2, journal)
    minipath = "%s/%s/%s" % (first, journal, fname)
    #minipath = "%s/%s" % (hex1, hex2)
    #minipath = "%s/%s" % (hex1, fname)
    #minipath = hex1
    #minipath = journal
    paths[minipath] = True
    
print lines, len(files), len(paths)

for letter, journals in journals_by_letter.items():
    print letter, len(journals)
    #if letter in ('a', 'b', 'e', 'i', 'm', 'p', 's'):
    #    print journals

print
for d1, d2 in duplicates:
    print d1
    print d2
    print
