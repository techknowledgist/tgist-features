# Count the number of files for each subject-year pair
# see count-subjects.txt for the result

echo 1995
cut -f1 -d' ' subject-lists/1995/* | sort | uniq -c
echo 1996
cut -f1 -d' ' subject-lists/1996/* | sort | uniq -c
echo 1997
cut -f1 -d' ' subject-lists/1997/* | sort | uniq -c
echo 1998
cut -f1 -d' ' subject-lists/1998/* | sort | uniq -c
echo 1999
cut -f1 -d' ' subject-lists/1999/* | sort | uniq -c
echo 2000
cut -f1 -d' ' subject-lists/2000/* | sort | uniq -c
echo 2001
cut -f1 -d' ' subject-lists/2001/* | sort | uniq -c
echo 2002
cut -f1 -d' ' subject-lists/2002/* | sort | uniq -c
echo 2003
cut -f1 -d' ' subject-lists/2003/* | sort | uniq -c
echo 2004
cut -f1 -d' ' subject-lists/2004/* | sort | uniq -c
echo 2005
cut -f1 -d' ' subject-lists/2005/* | sort | uniq -c
echo 2006
cut -f1 -d' ' subject-lists/2006/* | sort | uniq -c
echo 2007
cut -f1 -d' ' subject-lists/2007/* | sort | uniq -c
echo 2008
cut -f1 -d' ' subject-lists/2008/* | sort | uniq -c
echo 2009
cut -f1 -d' ' subject-lists/2009/* | sort | uniq -c
echo 2010
cut -f1 -d' ' subject-lists/2010/* | sort | uniq -c
echo 2011
cut -f1 -d' ' subject-lists/2011/* | sort | uniq -c
echo 2012
cut -f1 -d' ' subject-lists/2012/* | sort | uniq -c

