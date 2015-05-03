
year=1996

date
for fname in ../corpora/A07/$year/WoS.*; 
do
    echo "gzip $fname/*";
    gzip $fname/*
done
date
