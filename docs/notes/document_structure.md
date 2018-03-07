# Document Structure

The document structure parser is initiated with the `--xml2txt` option, which sets into motion the following chain of processing.

The main `step2_process.py` script calls the `xml2txt` method on the `corpus.Corpus` class. The `corpus` module takes care of all the bookkeeping like getting the input and output data sets, printing progress, checking whether the number of files we want to process is available in the input, updating the state of the data sets and uncompressing files if needed.

The `corpus` module also asks the `docstructure` a document structure parser (an instance of `docstructure.main.Parser`) given a couple of configuration options. Then, for each file, this parser is handed to the `xml2txt.xml2txt` function.

That function is basically a switch that decides what to do for a given data source:

- If the datasource is *ln* (a LexisNexis patent) then the document parser will process the document

- If the datasource is on of *wos*, *cnki*, *pm* and *signal-processing* (Web of Science, China National Knowledge Infrastructure, PubMed and WoS abstracts on signal processing is a different format than the other WoS datasource), then the document structure parser is bypassed and locally defined procedures are used to parse the structure.

Note that the document structure parser also deals with most of the formats under the second bullet point in addition to several types of data from Elsevier. The problem with the document structure parser however is that it is a tad over-engineered and hard to maintain and later changes were made directly to the `xml2txt` module. In time, the `docstructure` module will be deprecated and removed.
