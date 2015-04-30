"""

Create a file list that can be input to corpus creation.

Usage:

    python create-list.py FILENAME COUNT
    
FILENAME is the name of the output file and COUNT is the number of lines to take
from the PubMed master list, which is a randomly sorted list of 229K file paths.

The master list is

/home/j/corpuswork/fuse/FUSEData/lists/nxml-files-random.txt

It has relative paths to the files, those are made absolute by this script.

The result has short paths consisting of the first letter of the journal, the
journal name and the file name.

Duplicates for non-unique file names are not added. Note that we did not check
whether these were actual duplicates, we just ignore the few of those that are
there.

"""

import os, sys

DATADIR = '/home/j/corpuswork/fuse/FUSEData/2011-09/FUSEArchive'
LISTDIR = '/home/j/corpuswork/fuse/FUSEData/lists'
LISTFILE = LISTDIR + os.sep + 'nxml-files-random.txt'

out = open(sys.argv[1], 'w')
max_files = int(sys.argv[2])

lines = 0
files = {}
for line in open(LISTFILE):
    lines += 1
    if lines > max_files:
        break
    path_elements = line.strip().split(os.sep)
    hex1 = path_elements[2]
    fname = path_elements[-1]
    journal_plus_issue = path_elements[4]
    journal = journal_plus_issue.rstrip("_-1234567890")
    first = journal[0].lower()
    longpath = DATADIR + os.sep + line.strip()
    shortpath = "%s/%s" % (hex1, fname)
    shortpath = "%s/%s/%s" % (first, journal, fname)
    if files.has_key(shortpath):
        lines -= 1
        print "skipping duplicate", journal_plus_issue, fname
        continue
    else:
        files[shortpath] = True
        out.write("9999\t%s\t%s\n" % (longpath, shortpath))
