
for year in 1998 1999 2000 2001 2002 2003 2004 2005 2006 2007;
do
    echo python count_tokens.py /home/j/corpuswork/fuse/FUSEData/corpora/wos-cs-520k/subcorpora/$year
    python count_tokens.py /home/j/corpuswork/fuse/FUSEData/corpora/wos-cs-520k/subcorpora/$year
    echo python count_tokens.py /home/j/corpuswork/fuse/FUSEData/corpora/ln-us-cs-500k/subcorpora/$year
    python count_tokens.py /home/j/corpuswork/fuse/FUSEData/corpora/ln-us-cs-500k/subcorpora/$year
done
