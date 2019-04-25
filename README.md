# Techknowledgist Feature Extraction

Code to extract features for use in the Techknowledgist system.

This is a short introduction to get started, see the manual in `docs/manual/index.html` for more details.

You will need Python 2.7, Java 1.8, the Stanford tagger and segmenter and Git. Git is only needed for installation.

First clone the repository, initialize and update the submodules it uses, and copy the configuration file:

```sh
$ git clone https://github.com/techknowledgist/tgist-features
$ cd tgist-features
$ git submodule init
$ git submodule update
$ cp config-sample.py config.py
```

From the Stanford tools you need version 3.1.3 of the [tagger](http://nlp.stanford.edu/software/tagger.shtml) (the full version, not just the English version) and version 1.6.6 of the [segmenter](http://nlp.stanford.edu/software/segmenter.shtml). Later versions probably work, but have not been tested yet. Download the tools, unpack them and put them somewhere, making sure the path name does not include spaces. If you want to make the configuration step below trivial you could create a tools subdirectory and add the unpacked tools there.

Edit the contents of the configuration file (`config.py`) if needed. If you installed the Stanford tools in a `tools` subdirectory you won't need to do anything. Otherwise you need to set the `STANFORD_TAGGER_DIR` and `STANFORD_SEGMENTER_DIR` variables.

Now you can run the code on some example input:

```sh
$ python main.py -f data/lists/sample-us.txt -c data/sample-us
```

This takes the files listed in `data/lists/sample-us.txt` and creates feature vectors of all terms in those files in `data/sample-us`. See the manual for a description of the input and output.
