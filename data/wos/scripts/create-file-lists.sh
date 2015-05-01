# Create a file list from a directory.

# Edit assignments to $YEAR and $BASEDIR if needed.


YEAR=1995

TECHNOLOGER=/local/chalciope/marc/fuse/patent-classifier
BASEDIR=$TECHNOLOGER/ontology/doc_processing/data/wos
BASEDIR=/home/j/corpuswork/fuse/FUSEData/2013-04/wos

echo $YEAR + $BASEDIR

cd /

echo 'creating' $BASEDIR/file-lists/A01/$YEAR.txt
find $BASEDIR/corpora/A01/$YEAR | grep xml > $BASEDIR/file-lists/A01/$YEAR.txt

echo 'creating' $BASEDIR/file-lists/A04/$YEAR.txt
find $BASEDIR/corpora/A04/$YEAR | grep xml > $BASEDIR/file-lists/A04/$YEAR.txt

echo 'creating' $BASEDIR/file-lists/A07/$YEAR.txt
find $BASEDIR/corpora/A07/$YEAR | grep xml > $BASEDIR/file-lists/A07/$YEAR.txt

echo 'creating' $BASEDIR/file-lists/A10/$YEAR.txt
find $BASEDIR/corpora/A10/$YEAR | grep xml > $BASEDIR/file-lists/A10/$YEAR.txt

