#!/bin/csh -f

# Shell script to export a directory to a given destination. Running it from the parent
# directory will create an archive of the git repository with the following name
#
#     docstructure-SHA1.tar
#
# where SHA1 is the SHA-1 hash of the current head. This assumes (I think) that we are
# currently on the master branch since what is archived is the master branch. If not, the
# SHA1 value may be useless to find the code in git. Also note that non-commited changes
# will not be logged and will further reduce the likelyhood of re-creating the code.
#
# To inform the user on what is exported, the script prints the archive created, the git
# status on the working directory and the results of running the doc structure tests.
#
# This is a much simpler way of doing it than in build.sh, but there I wanted the script
# to be more sensitive to BAE needs and to how to replicate things.


set head = `git rev-parse HEAD`
set destination = $1
set archive = "$destination/docstructure-$head.tar"

echo ; echo "RUNNING DOCUMENT STRUCTURE EXPORTER"

echo ; echo "GIT STATUS:"
git status -bs

echo ; echo "RUNNING TESTS..."
python main.py -t

echo ; echo "CREATING ARCHIVE $archive..."
git archive master --prefix="docstructure/" > $archive

