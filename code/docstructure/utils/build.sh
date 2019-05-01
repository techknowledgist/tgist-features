#!/bin/csh -f

# Shell script to create a directory that can be sent off to users like BAE. Running it
# from the parent directory will create a directory docstructure-YYYYMMDD with all python
# scripts, some of the example data, and housekeeping data in the info directory (with
# git-related stuff). It prints the directory created and the git status on the working
# directory, the latter to make it easy for the user to relaize that what you are packagng
# is not versioned.
#
# TODO: should probably use git-archive in some way to make this more robust.


set version = `date +"%Y%m%d"`
set x = "docstructure-${version}"

echo ; echo "GIT STATUS:"
git status -bs

echo ; echo "CREATING DIRECTORY docstructure-$version..."
echo ; echo "COPYING FILES..."
mkdir $x ; cp *.py $x
mkdir $x/utils ; cp utils/*py $x/utils ; cp -r utils/standoff $x/utils
mkdir $x/readers ; cp readers/*py $x/readers
mkdir $x/data ; cp data/*.{txt,fact} $x/data
cp -r data/in $x/data
mkdir $x/data/tmp
mkdir $x/data/out
mkdir $x/data/html
mkdir $x/data/regression ; cp data/regression/* $x/data/regression

mkdir $x/info
git rev-parse HEAD > $x/info/head.txt
git status > $x/info/git-status.txt
git diff > $x/info/git-diff-working.txt
git diff --cached > $x/info/git-diff-cached.txt
git log --decorate --graph --all > $x/info/git-log.txt

echo ; echo "RUNNING TESTS..."
cd $x
python main.py -t

echo; echo "ARCHIVING $x..." ; echo
cd .. ; rm $x/*.pyc; rm $x/*/*.pyc ; tar cp $x | gzip > $x.tgz ; rm -R $x
