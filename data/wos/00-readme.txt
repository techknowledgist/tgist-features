Steps towards a bunch of subject domain specific corpora, most notable the
domains A01, A04, A06 and A10.


1. Run the indexer on all WoS archives

For example

	$ index.py WoS.out.2012000044.gz

There are batch scripts in scripts/ that do this. Move them to this directory,
run them, and they will populate index/ with directories for each year.

Note: the script makes the incorrect assumption that each record has only one
subject. This needs to be fixed and then this step, and probably all or most
below, will need to be redone. For now (April 17th, 2015) we will not bother
because of the time crush.

Note: the script does not extract publication times, we assume that the times
embedded in the archives is good enough.


2. Select the record identifiers for the three domains

Run one script once:

	$ python select-record-ids.py

This builds a directory subject-lists/ that mirrors index/.

Here is an idea of the total file count:

	$ cut -f1 -d' ' subject-lists/*/* | sort | uniq -c
	1595357 A01
	1883523 A04
	  24295 A06
	1123725 A10

Run count-subjects.sh for counts per year, it ignores A06 because it is so tiny.


3. Extract the records

Do this for every year:

	$ python select-record-files.py 1995

This builds the corpora in corpora/, which look like

	corpora/A01
	corpora/A01/1995
	corpora/A01/1995/WoS.out.1995000024
	corpora/A01/1995/WoS.out.1995000024/A1994BC72Q00010.xml
	corpora/A01/1995/WoS.out.1995000024/A1994BC72Q00001.xml
	corpora/A01/1995/WoS.out.1995000024/A1994BC72Q00012.xml

That is for each domain and each year, there are subdirectories for the archives
in which the individual files live.

See scripts/select-record-ids.sh for a full list. It is usually better to this
on a local disk, create the file lists (step 4) and then move it to the NSF
share.

Note: /home/j disk space started at 849GB


4. Create file lists

First the directories:

	mkdir file-lists
	mkdir file-lists/A01
	mkdir file-lists/A04
	mkdir file-lists/A07
	mkdir file-lists/A10

Then the lists:
	
	setenv TECHNOLOGER /local/chalciope/marc/fuse/patent-classifier
	setenv WOS $TECHNOLOGER/ontology/doc_processing/data/wos
	cd /
	find $WOS/corpora/A01/1995 | grep xml > $WOS/file-lists/A01/1995.txt
	find $WOS/corpora/A01/1996 | grep xml > $WOS/file-lists/A01/1996.txt
	...

The above works for when the corpora are in the local directory, replace the
first two lines with the following if the directories are on corpuswork

	setenv WOS /home/j/corpuswork/fuse/FUSEData/2013-04/wos/extracted/

You can use scripts/create-file-lists.sh to do this, but you would need minor
edits to the $YEAR variable.


5. Create file lists for corpus creation

Run:

	$ python create-corpus-filelist.py

The resulting file lists are randomly ordered.

Check years in output by

	$ cut -f1 file-lists-corpus/A01/1995.txt | sort | uniq -c

Should give just one year.


6. Compress the corpora

Use:

	gzip corpora/A01/1995/*/*
	gzip corpora/A04/1995/*/*
	gzip corpora/A10/1995/*/*

Oddly, this gives very modest gains, so we may skip it.


6. Initialize and process the corpus

Using step1_init.py and step2_process.py in doc_processing.
