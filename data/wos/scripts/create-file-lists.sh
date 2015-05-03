# Create a file list from a directory.

# Edit assignments to $BASEDIR if needed.


TECHNOLOGER=/local/chalciope/marc/fuse/patent-classifier
BASEDIR=$TECHNOLOGER/ontology/doc_processing/data/wos
BASEDIR=/home/j/corpuswork/fuse/FUSEData/2013-04/wos


cd /

for year in 1995 1996 1997 1998 1999 2000 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 2012;
do
    echo 'creating' $BASEDIR/file-lists/A01/$year.txt
    find $BASEDIR/corpora/A01/$year | grep xml > $BASEDIR/file-lists/A01/$year.txt
    echo 'creating' $BASEDIR/file-lists/A04/$year.txt
    find $BASEDIR/corpora/A04/$year | grep xml > $BASEDIR/file-lists/A04/$year.txt
    echo 'creating' $BASEDIR/file-lists/A07/$year.txt
    find $BASEDIR/corpora/A07/$year | grep xml > $BASEDIR/file-lists/A07/$year.txt
    echo 'creating' $BASEDIR/file-lists/A10/$year.txt
    find $BASEDIR/corpora/A10/$year | grep xml > $BASEDIR/file-lists/A10/$year.txt
done;

