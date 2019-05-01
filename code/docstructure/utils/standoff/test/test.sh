#!/bin/sh

rm -rf output
mkdir output 2> /dev/null

xsltproc ../text-content.xsl test.xml > output/test.txt
xsltproc ../standoff.xsl test.xml | xmllint --format - > output/standoff.xml
xsltproc --stringparam text "$(cat output/test.txt)" \
    ../inline.xsl output/standoff.xml > output/inline.xml
