# -*- coding: utf-8 -*-
"""
This is a simple wrapper for the Stanford Dependency Parser.

Upon initialization it opens a subprocess where it calls the SDP,
and it can be sent strings to parse using give_input()

Based on code from Amber Stubbs
astubbs@cs.brandeis.edu
last updated: August 25, 2009

PGA 3/27/2010
Added config.dat file from which to load configuration parameters
Added graph functions
location: /home/g/grad/anick/ie/sdp
PGA 5/17/2010
Replaced config.dat with sdp_config.py
Got the parser working for the case of generating tags, penn, and tdc output.
It would be better if the subprocess interaction were more robust.  Currently we
rely on the parser returning the expected format n order to complete reading output from 
subprocess.  It it hangs, look in log.dat for an error.
To make it robust, it might make sense to send stderr to stdout and check stdout for error messages. 
Send only debugging info to the log file.

At this point, for use with i2b2, we do the following:
# create an annotations instance named annot that
# loads in all the annotation and txt data for i2b2.
>>> reload i2b2_main
# create an easy to type handle for it
>>> a = i2b2_main.annot
# Dump the txt and subtxt files out in a form
# ready for use by sdpWrapper
>>> a.subtxt2sdp_input_format("subtxt.sdp_in")
>>> a.txt2sdp_input_format("txt.sdp_in")
# load sdpWrapper (on a fast machine like themis)
>>> import sdpWrapper
# If any changes are made in sdpWrapper, reload
>>> reload(sdpWrapper)
<module 'sdpWrapper' from 'sdpWrapper.py'>
# invoke the parser with the specific outputFormat string.  
>>> dparser = sdpWrapper.sdpWrapper("wordsAndTags,penn,typedDependenciesCollapsed")
in init, tagcmd: java -mx300m -cp /home/g/grad/anick/ie/stanford-parser-2010-02-26/stanford-parser.jar: edu.stanford.nlp.parser.lexparser.LexicalizedParser -outputFormat "wordsAndTags,penn,typedDependenciesCollapsed" /home/g/grad/anick/ie/stanford-parser-2010-02-26/englishPCFG.ser.gz  - 2>log.dat
# Do the parse of txt and subtxt
# This creates output files
>>> dparser.parse_i2b2_file("subtxt.sdp_in", "subtxt")
>>> dparser.parse_i2b2_file("txt.sdp_in", "txt")


"""

import sys, os, re
from subprocess import Popen, PIPE, STDOUT, call
import pickle
import pdb

import config


# debug_p value for sdpWrapper instance 
debug_p = 1

# To align sdp token nos with tokens starting at index 0, we need to 
# add the token_no_offset of -1.  To use the sdp token numbering, set this to 0
token_no_offset = -1
#token_no_offset = 0

# Note we cannot use nested classes with pickle, so 
# link and node were taken from inside sdpGraph and defined
# at the top level

os.environ['PYTHONIOENCODING'] = 'utf-8'

# link connects two nodes via a relation
# No longer used??
class link:
    def __init__(self, rel, parent, child):
        self.rel = rel
        self.parent = parent
        self.child = child

class node:
    # loc is numerical offset in sentence
    # word is its string
    # parent is the parent relation
    # children are child relations
    def __init__(self, id, word, loc):
        """
        if debug_p:
            print "init node: id %s" % (id)
        """
        self.id = id
        self.word = word
        self.loc = int(loc)
        # list of [rel node-id] pairs
        self.children = []
        # empty list for parent indicates root node
        # normally, parent is a list with two elements [rel node-id]
        self.parent = []


class sdpGraph:
    debug_p = 1

    def add_link(self, rel, pnode, cnode):
        if sdpGraph.debug_p:
            print "add_link: rel %s, pnode %s (%s), cnode %s (%s)" % (rel, pnode.id, pnode, cnode.id, cnode)
        # add rel info to parent and child nodes
        pnode.children.append([rel, cnode])
        cnode.parent = [rel, pnode]
           
    # word-id from sdp is of the form <word>-<number>
    # In cases of conjunction, the same word may be the subject of multiple verbs so
    # SDP creates a new token with ' appended.
    # /// note that this raises an issue what to do when mapping token_no to id
    def id2word_loc(self, word_id):
        if sdpGraph.debug_p:
            print "id2word: word_id |%s|" % word_id

        # for some odd cases involving punctuation, we get empty strings
        # showing up in the sdp output, so we have to test for that case here
        if word_id == "":
            return ["", "", 0]
        # We also run into the case (especially with punc like ".") where the numeric id is missing
        elif word_id.find('-') == -1:
            return ["", "", 0]
        else:

            ####print "id2word_loc: word_id %s" % word_id 
            # note we use rpartition in python 2.6 instead of split since some
            # tokens may contain legitimate hyphens (four-star-14)
            #word_fields = word_id.rpartition("-")
            #token = word_fields[0]
            #number_suffix = word_fields[2]

            # To be compatible with python 2.4 on themis, I rewrote the above lines
            token = word_id[0:word_id.rfind("-")]
            number_suffix = word_id[word_id.rfind("-")+1:]

            if sdpGraph.debug_p:
                print "in sdpGraph: token: %s, number_suffix: |%s|" % (token, number_suffix)


            if number_suffix[-1] == "'":
                suffix = "'"
                number_suffix = number_suffix[0:-1]
            else:
                suffix = ""

            token_no = int(number_suffix)
            offset = self.token_no_offset
            if offset != 0:
                # apply the offset to the token number
                token_no = token_no + self.token_no_offset
                if sdpGraph.debug_p:
                    print "id2word_loc: applied token_no offset adjustment"
            token_id = token + "-" + str(token_no) + suffix
            
            return [token_id, token, token_no]


    # rel_list is a list of the relations from the sdg [[rel node_id1 node_id2] ...]
    def __init__(self, rel_list):
        if sdpGraph.debug_p:
            print "Entered init graph with rel_list: %s" % rel_list
        # graph is composed of nodes (words) and links (of type p: parents and c: children)
        # key is node_id (usually word-loc)
        self.nodes = {}
        # also create a map from loc to token_id.  This allows us to tie into other
        # representations based on token location (start/end)
        self.loc2id = {}

        # keep track of links that can lead to cycles
        self.recursive_links = ["rcmod"]

        # The token_no_offset should be set in a config file
        # but for now we take it from a glabal in this module
        self.token_no_offset = token_no_offset

        # now add all the nodes and links from the stanford dependency parse
        for rel_fields in rel_list:
            rel = rel_fields[0]
            (pword_id, pword, ploc) = self.id2word_loc(rel_fields[1])
            (cword_id, cword, cloc) = self.id2word_loc(rel_fields[2])
            # test for the odd case where one of the ids is null string and
            # ignore it.  This happens occasionally in phrases with many punctuations.
            if (pword_id != "") and (cword_id != ""):
                # first make sure both nodes exist (or create them)
                if not self.nodes.has_key(pword_id):
                    # create the parent node and add it to the nodes dict
                    pnode = node(pword_id, pword, ploc)
                    self.nodes[pword_id] = pnode
                if not self.nodes.has_key(cword_id):
                    # create the parent node and add it to the nodes dict
                    cnode = node(cword_id, cword, cloc)
                    self.nodes[cword_id] = cnode
                # get the nodes and add the relation
                pnode = self.nodes.get(pword_id)
                cnode = self.nodes.get(cword_id)
                self.add_link(rel, pnode, cnode)
                # Now add the location info
                """
                if debug_p:
                    pword_loc_str = pword_id[pword_id.rfind("-")+1:]
                    loc = pword_id.rfind("-")
                    print "pword: |%s|, loc: |%s|, pword_loc(str): %s" % (pword_id, loc, pword_loc_str)
                """

                ### /// we need to fix this to allow locs to map to multiple
                ### ids in the case of coordinations (where sdp uses a token id
                ### with single quote appended to create a new token id).
                trimmed_pword_id = pword_id.rstrip("'")
                trimmed_cword_id = cword_id.rstrip("'")
                pword_loc = int(trimmed_pword_id[trimmed_pword_id.rfind("-")+1:])
                self.loc2id[pword_loc] = pword_id
                cword_loc = int(trimmed_cword_id[trimmed_cword_id.rfind("-")+1:])
                self.loc2id[cword_loc] = cword_id

    def print_graph(self):
        for key in self.nodes.keys():
            print "key: %s" % key
            node = self.nodes.get(key)
            if debug_p:
                print "print_graph: id: %s, self: %s, parent: %s " % (node.id, node, node.parent)
            # get parent info
            if node.parent != []:
                rel = node.parent[0]
                if debug_p:
                    print "print_graph parent %s, rel %s" % (node.parent, rel)
            

                parent = node.parent[1]
                pnode_id = parent.id
            
                print "   parent: %s (%s)" % (pnode_id, rel)
            else:
                print "   parent: ROOT"

            print "   children: "
            for child in node.children:
                # print rel and node-id of child
                print "      %s: %s" % (child[0], child[1].id)


    def get_path(self, n1, n2):
        # We'll find a path by following both nodes up to the root, then looking for the
        # deepest shared node between the two.
        n1_parent_list = []
        n1_ancestors = [n1]
        n1_rel_list = []
        n2_rel_list = []
        n2_parent_list = []
        node = n1
        if sdpGraph.debug_p:
            print "get_path: n1 id: %s, parent_id: %s" % (node.id, node.parent)

        rel_parent = node.parent
        # we have to check for cycles by testing if parent node is already in n1_ancestors
        while rel_parent != [] and rel_parent[1] not in n1_ancestors:
            node = rel_parent[1]
            rel_info = ["+", rel_parent[0], node, node.word]
            n1_ancestors.append(node)
            n1_parent_list.append(rel_info)
            n1_rel_list.append("+" + rel_parent[0])
            rel_parent = node.parent
            if sdpGraph.debug_p:
                print "n1: parent %s" % node.id

        node = n2
        if sdpGraph.debug_p:
            print "get_path: n2 id: %s, parent_id: %s" % (node.id, node.parent)

        n2_ancestors = [n2]
        rel_parent = node.parent
        # we have to check for cycles by testing if parent node is already in n2_ancestors
        while rel_parent != [] and node not in n1_ancestors and rel_parent[1] not in n2_ancestors:
            node = rel_parent[1]
            n2_ancestors.append(node)
            rel_info = ["-", rel_parent[0], node, node.word]
            n2_rel_list.append("-" + rel_parent[0])
            n2_parent_list.append(rel_info)
            rel_parent = node.parent
            if sdpGraph.debug_p:
                print "n2: parent %s" % node.id

        # determine if/where the paths intersect
        # note that n2 loop can exit when an ancester is encountered AND
        # the parent is [], so we need to test on whether ancestor was encountered
        # to determine whether there was an intersection or not.
        if  node not in n1_ancestors:
            # print "no intersection"
            # return empty paths
            return(["", []])
        else:
            # n2 ancestor node was encountered in n1_ancestors
            shared_node_index = n1_ancestors.index(node)
            # So the path from n1 to n2 is all ancestors from n1 up to this index
            path = n1_ancestors[0:shared_node_index + 1]
            # print "shared_node_index: %i, path: %s" % (shared_node_index, path)

            # compute the path
            path = n1_parent_list[0:shared_node_index]
            n2_parent_list.reverse()
            path.extend(n2_parent_list)
            # print "[get_path] path: %s" % path

            rel_path = n1_rel_list[0:shared_node_index]
            n2_rel_list.reverse()
            rel_path.extend(n2_rel_list)
            # print "[get_path]  rel_path: %s" % rel_path
            # print "n1_rel_list: %s" % n1_rel_list
            # print "n2_rel_list: %s" % n2_rel_list
            return([rel_path, path])


    # given token location, return the word of its parent node
    def get_lparent(self, loc):
        id = self.loc2id.get(loc)
        node = self.nodes.get(id)
        parent = node.parent
        if parent != []:
            rel = parent[0]
            word = parent[1].word
            return(rel, word)
        else:
            return("", "")
            
    def get_lpath(self, loc1, loc2):
        id1 = self.loc2id.get(loc1)
        id2 = self.loc2id.get(loc2)
        n1 = self.nodes.get(id1)
        n2 = self.nodes.get(id2)
        # print "get_lpath: %s" % self.get_path(n1, n2)

        if sdpGraph.debug_p:
            print "get_lpath: loc1 |%i|, id1 |%s|, loc2 |%i|, id2 |%s|" % (loc1, id1, loc2, id2)
        # In some cases a word in the sentence does not have a node in the graph (e.g. the word "that" as relative
        # clause introducer).  If either id is "None", then return null strings as the paths ["", []]
        if (n1 is None) or (n2 is None):
            return(["", []])
        else:
            # compute and return the paths
            return(self.get_path(n1, n2))

    def get_lpath_string(self, loc1, loc2):
        (rel_path, path) = self.get_lpath(loc1, loc2)
        rel_path_string = ""
        for rel in rel_path:
            rel_path_string = rel_path_string + rel
        return(rel_path_string)
            
        



class sdpWrapper:


    def get_config(self):
        # use defaults in config.py
        self.sdp_dir = config.sdp_dir
        self.tokenized = config.STANFORD_TOKENIZED
        self.mx = config.STANFORD_MX
        self.tag_separator = config.STANFORD_TAG_SEPARATOR
        self.sentences = config.STANFORD_SENTENCES
        self.debug_p = config.STANFORD_DEBUG_P
        global debug_p
        debug_p = 0



    # From http://nlp.stanford.edu/nlp/javadoc/javanlp/edu/stanford/nlp/parser/lexparser/package-summary.html
    # output format can be any comma separated string containing
    # penn, oneline, wordsAndTags, latexTree, typedDependenciesCollapsed, typedDependencies

    def __init__(self, output_format = "wordsAndTags,penn,typedDependenciesCollapsed"):
        #pdb.set_trace()
        # PGA modified to use config data
        self.get_config()
        #print "\n\ninitializing sdpWrapper--init()\n"

        # set tokenized_p to 1 if sentence is already tokenized, otherwise 0 (default).        
        if self.tokenized == 1:
            tokenized_flag = " -tokenized "
        else:
            tokenized_flag = ""

        if self.tag_separator != "":
            # add -tagSeparator option to call
            tag_separator_option = " -tagSeparator " + self.tag_separator + " "
        else:
            tag_separator_option = ""
            
        if self.sentences != "":
            sentences_option = " -sentences " + self.sentences
        else:
            sentences_option = ""

        # This command needs to be adjusted to run the latest release.  Check documentation and sample lang.sh script there.
        tagcmd = ('java -mx' + self.mx + ' -cp ' + self.sdp_dir + '/stanford-parser.jar: '  + 'edu.stanford.nlp.parser.lexparser.LexicalizedParser' + sentences_option + tokenized_flag + tag_separator_option +  ' -outputFormat '  + '"' + output_format + '" ' + self.sdp_dir + '/englishPCFG.ser.gz  - 2>log.dat')



            # PGA added maxLength option
            # tagcmd = ('java -mx' + self.mx + ' -cp ' + self.sdp_dir + '/stanford-parser.jar: '  + 'edu.stanford.nlp.parser.lexparser.LexicalizedParser' + sentences_option + tokenized_flag + tag_separator_option + ' -maxLength 40' + ' -outputFormat '  + '"' + output_format + '" ' + self.sdp_dir + '/englishPCFG.ser.gz  - 2>log.dat')

        #tagcmd = ('java -mx' + self.mx + ' -cp ' + self.sdp_dir + '/stanford-parser.jar: '  + 'edu.stanford.nlp.parser.lexparser.LexicalizedParser' + sentences_option + tokenized_flag + tag_separator_option + ' -outputFormat '  + '"typedDependencies" ' + self.sdp_dir + '/englishPCFG.ser.gz  - 2>log.dat')
        
        if self.debug_p:
            print "in init, tagcmd: %s" % tagcmd

#        tagcmd = 'java -mx150m -cp ./blinker/sdp/stanford-parser.jar: edu.stanford.nlp.parser.lexparser.LexicalizedParser -outputFormat "typedDependencies" ./components/blinker/sdp/englishPCFG.ser.gz - '
#        self.p = Popen(tagcmd, shell=True, stdin=PIPE, stdout=PIPE)
        
        # create a subprocess that reads from stdin and writes to stdout
        self.proc = Popen(tagcmd, shell=True, stdin=PIPE, stdout=PIPE, universal_newlines = True)


    def process(self, text):
        self.give_input_and_tilda(text)
        return self.get_output()
        #return self.get_outputs()


    def process_to_end(self, text):
        print "[process_to_end]text: %s" % text
        self.give_input_and_end(text)
        print "[process_to_end]after give_input_and_end"
        result = self.get_output_to_end()
        #print "[process_to_end]after setting result to: %s" % result
        return(result)

        #return self.get_outputs()


    # passes a string to the sdp tagger subprocess
    # Also passes a special "~" string to use as a signal that tag output
    # is finished.
    def give_input_and_end(self,text):
        #self.proc.stdin.flush()
        terminated_line = text+'\n~\n'
        print "[give_input_and_end]terminated_line: |%s|" % terminated_line
        self.proc.stdin.write(terminated_line)
        #self.proc.stdin.write(text)
        self.proc.stdin.flush()


    # Reads lines from the output of the subprocess (sdp parser) and 
    # concatenates them into a single string, returned as the result
    # We use a line with a single "~" to signal the end of the output
    # from the tagger.  Note that the tagger will add _<tag> to the tilda,
    # so we match on the first two characters only for the termination condition.
    def get_output_to_end(self):
        ###print "[get_output] entered..."
        result=""
        #line = self.proc.stdout.readline()
        #line = self.proc.stdout.readline().decode('utf8')
        line = self.proc.stdout.readline().decode(sys.stdout.encoding)
        line = self.proc.stdout.readline()
        line = unicode(line)

        #print "[tag: get_output_to_end]line is: |%s|" % line
        #while len(line)>2 :
        while True:

            # remove tabs from sdp output (e.g. for Phrase structure)
            line = line.strip("\n")
            line = line.lstrip()

            if line[0:2] =="~_": break


            print "[get_output_to_end]in while loop.  line: |%s|" % line
            #result=result+line
            result=result + "\t" + line
            print "[get_output_to_end]result: |%s|" % result
            #line = self.proc.stdout.readline()
            #line = self.proc.stdout.readline().decode('utf8')
            line = self.proc.stdout.readline().decode(sys.stdout.encoding)
            line = self.proc.stdout.readline()
            line = unicode(line)
            print "[get_output_to_end]next line: |%s|" % line


        print "[get_output_to_end]Out of loop.  Returning..."
        return result[1:]



    # Reads lines from the output of the subprocess (sdp parser) and 
    # concatenates them into a single string, returned as the result
    def get_output(self):
        ###print "[get_output] entered..."
        result=""
        line = self.proc.stdout.readline()
        while line != "~\n":
        #while len(line)>2 :
        #while len(line)>0 :

            line = line.strip("\n")
            #result=result+line
            # remove tabs from sdp output (e.g. for Phrase structure)
            line = line.lstrip()
            result=result + "\t" + line
            ###print "[get_output]result: %s" % result
            line = self.proc.stdout.readline()

        # results = result.split("\n")
        # for rel in results:
        #    print "RESULT = "+rel

        # use [1:] to strip the initial tab from the result
        #print "[get_output] result: %s" % (result[1:])

        return result[1:]

    # use this if wordAndTags is the parse option
    def get_output_tags(self):
        #print "[get_output_tags] entered..."
        result=""
        line = self.proc.stdout.readline()
        while len(line)>2 :
            line = line.strip("\n")
            #result=result+line
            # remove tabs from sdp output (e.g. for Phrase structure)
            line = line.lstrip()
            result=result + "\t" + line
            #print "[get_output]result: %s" % result
            line = self.proc.stdout.readline()

        # results = result.split("\n")
        # for rel in results:
        #    print "RESULT = "+rel

        # use [1:] to strip the initial tab from the result
        #print "[get_output] result: %s" % (result[1:])

        return result[1:]





    # TODO:  set up an output function that given a text returns the tags and deps in a single
    # tab separated line each ///

    # currently this function will only work when the output format is
    # "wordsAndTags,penn,typedDependenciesCollapsed"
    # which produces 3 forms of parsed output
    def get_outputs(self):
        # print "[get_outputs] entered..."
        # assume 3 results, separated by empty newline lines
        # outputs = ["a", "b", "c"]
        # use two parameters if testing the -tokenized option
        # and only requesting penn,typedDependenciesCompressed output
        #outputs = ["b", "c"]
        result_list = []
        for o in range(0, 3):
            # print "[get_outputs] for %s" % o
            #pdb.set_trace()
            each_result = self.get_output()
            result_list.append(each_result)
        return result_list

    def get_output_dep(self):
        # print "[get_output_dep] entered..."
        result=""
        line = self.proc.stdout.readline()
        while len(line)>2 :
            line = line.strip("\n")
            result=result + "\t" + line
            line = self.proc.stdout.readline()
        results = result.split("\n")
        for rel in results:
            print "RESULT = "+rel


        # print "[get_output_dep] result: %s" % result

        return result

    def get_output_penn_oneline(self):
        # print "[get_output_penn_oneline] entered..."
        result=""
        line = self.proc.stdout.readline()
        while len(line)>2 :
            line = line.strip("\n")
            result=result + "\t" + line
            line = self.proc.stdout.readline()
        results = result.split("\n")
        for rel in results:
            print "RESULT = "+rel


        # print "[get_output_penn_oneline] result: %s" % result
        return result
            
    # passes a string to the sdp parser subprocess
    def give_input(self,text):
        #self.proc.stdin.flush()
        self.proc.stdin.write(text+'\n')
        self.proc.stdin.flush()


    # passes a string to the sdp parser subprocess
    # Also passes a special "~" string to use as a signal that parse output
    # is finished.
    def give_input_and_tilda(self,text):
        #self.proc.stdin.flush()
        self.proc.stdin.write(text+'\n~\n')
        self.proc.stdin.flush()

        
    # takes the string returned by get_output (dependency parse)
    # and creates a graph
    # Each line of the sdp output is of the form:
    # nsubj(forced-23, rain-3)
    def get_graph(self, sdpout):
        
        sdpout = sdpout.rstrip("\n")
        rel_list = []
        lines = sdpout.split("\n")
        if self.debug_p:
            print "**In get_graph, lines: "
            for line in lines:
                print "%s" % line

        for line in lines:
            # find indexes of the separator chars in the sdp format
            #print "line of sdpout is: %s" % line
            i_end_of_rel = line.find("(")
            i_start_of_arg1 = i_end_of_rel + 1
            i_end_of_arg1 = line.find(", ")
            i_start_of_arg2 = i_end_of_arg1 + 2
            i_end_of_arg2 = line.rfind(")")
            rel = line[0:i_end_of_rel]
            arg1 = line[i_start_of_arg1:i_end_of_arg1]
            arg2 = line[i_start_of_arg2:i_end_of_arg2]
            #print "i1, i2, i3, rel, arg1, arg2 = %s, %s, %s, %s, %s, %s" % (i_end_of_rel, i_end_of_arg1, i_end_of_arg2, rel, arg1, arg2)
            rel_list.append([rel, arg1, arg2])

        graph = sdpGraph(rel_list)
        return(graph)




    # takes the string returned by get_output for typedDependenciesCollapsed (using tabs
    # to separate lines)
    # and creates a graph
    # The sdp output is a tab separated list of dependencies of the form:
    # nsubj(forced-23, rain-3)
    def tdc2graph(self, tdc_out):
        
        tdc_out = tdc_out.rstrip("\n")
        rel_list = []
        lines = tdc_out.split("\t")
        if self.debug_p:
            print "In get_graph, lines: "
            for line in lines:
                print "%s" % line

        for line in lines:
            # find indexes of the separator chars in the sdp format
            #print "line of sdpout is: %s" % line
            i_end_of_rel = line.find("(")
            i_start_of_arg1 = i_end_of_rel + 1
            i_end_of_arg1 = line.find(", ")
            i_start_of_arg2 = i_end_of_arg1 + 2
            i_end_of_arg2 = line.rfind(")")
            rel = line[0:i_end_of_rel]
            arg1 = line[i_start_of_arg1:i_end_of_arg1]
            arg2 = line[i_start_of_arg2:i_end_of_arg2]
            #print "i1, i2, i3, rel, arg1, arg2 = %s, %s, %s, %s, %s, %s" % (i_end_of_rel, i_end_of_arg1, i_end_of_arg2, rel, arg1, arg2)
            rel_list.append([rel, arg1, arg2])

        graph = sdpGraph(rel_list)
        return(graph)





    def quit(self):
        self.proc.terminate()



    def test0(self):

        print "sentence 1\n"

        self.process_to_end('John went to school today. \nAnother sentence exists.')
        #self.give_input_and_end('John went to school today.')
        #result = self.get_output_to_end()
        #print result
        
        print "sentence 2\n"
        
        self.process_to_end('Mary went to school yesterday. Another sentence occurs!')
        #self.give_input('Mary went to school yesterday. Another sentence occurs!')
        #result = self.get_output()
        #print result


        
    def test1(self):

        print "sentence 1\n"
        
        self.give_input('John went to school today.')
        result = self.get_output()
        print result
        
        print "sentence 2\n"
        
        self.give_input('Mary went to school yesterday. Another sentence occurs!')
        result = self.get_output()
        print result
        

        print "sentence 3\n"
        
        self.give_input("The two nations are the world 's largest emitters of the pollution blamed for global warming, but so far China has resisted calls to set specific caps on emissions or to eliminate tariffs on clean energy technology that the United States and other countries would like to sell them .")
        result = self.get_output()
        print result


    def test2(self):
        self.give_input("(in parens), George W. Bush's father met with The Federation of Chess Players, in Boseman, Montana this past Thursday evening.  He returns tonight.  Tomorrow he will leave.")
        # parsed incorrectly!
        #self.give_input("Subject ate object.")

        #self.give_input("John ate dinner.")
        result = self.get_output()
        #print "result: %s" % result
        graph = self.get_graph(result)
        graph.print_graph()


    def test3(self):
        # gives token id agreed-3'
        self.give_input("Iraq has agreed to allow all 880 Soviets in Kuwait to leave , but only by a 1,200-mile road route through Iraq and to the Iraq-Jordan border .")
        # sdp does a bad job on this one (conjunctions)
        #self.give_input("Iraq sent messages and relayed notes and played records .")
        #self.give_input("Iraq has agreed to allow all 880 Soviets in Kuwait to leave , but only by a 1,200-mile road route .")
        #self.give_input("Iraq has agreed to allow all 880 Soviets in Kuwait to leave , but only by a 1,200-mile road route through Iraq  .")

        #self.give_input("Iraq has agreed to allow all 880 Soviets in Kuwait to leave , but only by a 1,200-mile road route through Iraq and left .")
        # self.give_input('Mary went to school yesterday.\n  She returned today. \n John saw her.')
        # self.give_input("` ` We do n 't just arrive , ' ' said four-star Gen. John Dailey , assistant commandant of the U.S. Marine Corps .")

        """
        # Does sdp output Jakarta and Indonesia?

        self.give_input("JAKARTA , Indonesia (AP ) _ The youngest son of ex-dictator Suharto disobeyed a summons to surrender himself to prosecutors Monday and be imprisoned for corruption .")
        result = self.get_output()
        """

    #### active test #####
    def test5(self):
        # Sentence with many terms with no_rel
        self.give_input("The person who submits the winning name , which Towne said should evoke the elephant 's Asian heritage , will receive a trip for two to Thailand , where Chai is from .")
        result_list = self.get_outputs()
        
        print result_list
        
        graph = self.tdc2graph(result_list[2])
        graph.print_graph()
        return(graph)

    def test6(self):
        print "sentence 1\n"
        #self.give_input('He_PRP decided_VBD that_IN fashion_NN has_VBZ a_DT silver_NN lining_VBG __NN and_CC exterior_NN ,_, as_RB well_RB ._.')
        #self.give_input('He/PRP decided/VBD that/IN fashion/NN has/VBZ a/DT silver/NN lining/VBG _/NN and_CC exterior/NN ,/, as_RB well/RB ./.')
        self.give_input('He decided that fashion has a silver lining _ and exterior , as well .')
        result = self.get_output()
        print result

    def test7(self):        
        self.give_input('Mary went to school yesterday .')
        result = self.get_output()
        print result
    
    def test8(self):

        print "sentence 3\n"
        
        self.give_input("The two nations are the world 's largest emitters of the pollution blamed for global warming, but so far China has resisted calls to set specific caps on emissions or to eliminate tariffs on clean energy technology that the United States and other countries would like to sell them .")
        result = self.get_output()
        print result


    def test9(self):
        self.give_input("(in parens), George W. Bush's father met with The Federation of Chess Players, in Boseman, Montana this past Thursday evening.  He returns tonight.  Tomorrow he will leave.")
        # parsed incorrectly!
        #self.give_input("Subject ate object.")

        #self.give_input("John ate dinner.")
        result = self.get_output()
        #print "result: %s" % result
        graph = self.get_graph(result)
        graph.print_graph()

    #### For these tags, set the appropriate config parameters and adjust get_outputs to a list with two items.
    # test for input with tags
    def test10(self):
        # tags from original sdp output
        self.give_input("She/PRP was/VBD PROBLEM_1/NN and/CC TEST_2/NN were/VBD stable/JJ ./. ")
        result_list = self.get_outputs()
        
        print result_list

    # test for input with tags
    def test11(self):
        # tags modified by hand
        self.give_input("She/PRP was/VBD PROBLEM_1/JJ and/CC TEST_2/NN were/VBD stable/JJ ./. ")
        result_list = self.get_outputs()
        print result_list

    # test for input with tags
    def test12(self):
        # tags modified by hand
        self.give_input("He/PRP was/VBD young/JJ ./. ")
        result_list = self.get_outputs()
        print result_list

    # test for input with tags
    def test12(self):
        # words with **
        self.give_input("I am managing this critically ill **AGE[in 40s]- year - old male with pancreatitis")
        result_list = self.get_outputs()
        print result_list

    def test13(self):
        sents_file = "/home/j/anick/fuse/data/patents/en/sents/US4192770A.txt"
        tags_file = "/home/j/anick/fuse/data/patents/en/tags/US4192770A.txt"
        self.tag_file(sents_file, tags_file)            


    """
    # sent_file is a file with one sentence per line
    # doc_id\tsent_no\tsent (where sent is whitespace separated string of tokens)
    # corpus_file is an output file where the pickled list of graphs is written

    def parse_sent_file(self, sent_file, corpus_file):
        cdb = corpus_db()

        s_sents = open(sent_file, "r")
        # sent_file line is doc_id\tsent_id\tsent
        
        # accumulate sentence for each doc_id
        sent_list = []
        current_doc_id = ""
        for line in s_sents:
            line = line.strip("\n")
            (doc_id, sent_id, sent) = line.split("\t")
            self.give_input(sent)
            result = self.get_output()
            graph = self.get_graph(result)

            if doc_id != current_doc_id:
                print "starting doc: %s" % doc_id
                if current_doc_id != "":
                    # write out the list of sents for this doc_id
                    # except for transition to the very first doc_id,
                    # where current_doc_id == ""
                    cdb.add_doc(current_doc_id, sent_list)
                sent_list = []
                current_doc_id = doc_id

            sent_list.append(graph)

        # handle the last doc
        cdb.add_doc(doc_id, sent_list)
            

        # pickle and output graph list
        s_corpus = open(corpus_file, 'w')
        # graph list is an ordered list of triples [doc_id. sent_no. graph]
        pickle.dump(cdb, s_corpus)
        s_corpus.close()

    """

    # sent_file contains one or more sentences per line
    # writes tagged tokens to output_file
    def tag_file(self, sent_file, output_file):
        max_length = 80

        s_sents = open(sent_file, "r")
        s_tag = open(output_file + ".tag", "w")
        s_over = open(output_file + ".over", "w")

        for line in s_sents:
            line = line.strip("\n")
            if len(line) > 0:
                token_list = line.split(" ")
                if len(token_list) <= max_length:
                    self.give_input(line)
                    tags  = self.get_output()

                    s_tag.write("%s\n" % ( tags ))
                else:
                    # overflow
                    s_over.write("%s\n" % (line))
        s_tag.close()
        s_over.close()

    # i2b2_file is a file with one sentence per line
    # txt txt_no doc_id tsent_no\tsent (where sent is whitespace separated string of tokens)
    # e.g. subtxt 20 018636330_DH 57         She has no PROBLEM_1 .
    # corpus_file is an output file where the pickled list of graphs is written.
    # We assume the parser has been initialized as follows:
    # dparser = sdpWrapper.sdpWrapper("wordsAndTags,penn,typedDependenciesCollapsed")
    # Note that if the parser cannot parse an input, it writes to stderr (log.dat)
    # and the subprocess hangs waiting for stdout.  SO we try to avoid this situation by
    # checking the length of sentences and not sending any over max_length to the parser.
    # The parser's stated max length is 100 but we can be safer by choosing a lower threshold.

    # NOTE: PGA 5/17/10 For convenience, we output both readable files and a pickled file 
    # containing everything within a cdb instance object here.
    def parse_i2b2_file(self, sent_file, output_file):
        max_length = 80
        
        # data structure to hold all parse data for output to pickle file
        ### cdb = corpus_db()

        s_sents = open(sent_file, "r")
        s_tag = open(output_file + ".tag", "w")
        s_penn = open(output_file + ".penn", "w")
        s_tdc = open(output_file + ".tdc", "w")
        s_over = open(output_file + ".over", "w")

        for line in s_sents:
            line = line.strip("\n")
            (meta_data, sent) = line.split("\t")
            token_list = sent.split(" ")
            if len(token_list) <= max_length:
                self.give_input(sent)
                (tags, penn, tdc)  = self.get_outputs()
                ####graph = self.tdc2graph(tdc)

                s_tag.write("%s\t\t%s\n" % ( meta_data, tags))
                s_penn.write("%s\t\t%s\n" % ( meta_data, penn))
                s_tdc.write("%s\t\t%s\n" % ( meta_data, tdc))
            else:
                # overflow
                s_over.write("%s\n" % (line))
        s_tag.close()
        s_penn.close()
        s_tdc.close()
        s_over.close()

        """
        # pickle and output graph list
        s_corpus = open(corpus_file, 'w')
        # graph list is an ordered list of triples [doc_id. sent_no. graph]
        pickle.dump(cdb, s_corpus)
        s_corpus.close()
        """
        
# file prefix should contain full directory path but not the file extensions.
# We assume that txt.tdc and subtxt.tdc files in the directory are to be 
# turned into graphs and pickled along with .tag and .penn data
#def pickle_i2b2_parse_files(file_prefix):
#///    



####################################

def doc2sent_id (doc_id, sent_no):
    sent_id = doc_id + "_" + str(sent_no)
    return(sent_id)

# graph database
###/// incomplete
# PGA 5/17/10 replacing corpus_db with parse_db for i2b2 data
class parse_db:
        
    def __init__(self):
        # dict given a txt or subtxt no and returning metadata and a line
        self.d_txt_no2pline = {}
        self.d_subtxt_no2pline = {}
        """
        self.d_txt_no2tag = {}
        self.d_txt_no2penn = {}
        self.d_txt_no2tdc = {}
        self.d_txt_no2tdc_graph = {}

        self.d_subtxt_no2tag = {}
        self.d_subtxt_no2penn = {}
        self.d_subtxt_no2tdc = {}
        self.d_subtxt_no2tdc_graph = {}
        """

    def get_node(self, graph, token_no, word):
        token_id = word  + "-" + str(token_no)
        #print "get_node: type: |%s|, token_id %s" % (type(graph), token_id)
        #for key in graph.nodes.keys():
        #    print "key: %s" % key
        node = graph.nodes.get(token_id)
        return node

    """
    # include final slash in path
    def import_i2b2_dir(self, path):
        s_txt_tag = open(path + "txt.tag")
        s_txt_penn = open(path + "txt.penn")
        s_txt_tdc = open(path + "txt.tdc")
        s_txt_over = open(path + "txt.over")
        s_subtxt_tag = open(path + "subtxt.tag")
        s_subtxt_penn = open(path + "subtxt.penn")
        s_subtxt_tdc = open(path + "subtxt.tdc")
        s_subtxt_over = open(path + "subtxt.over")

        
        for line in s_txt_tag:
            line = line.strip("\n")


        s_txt_tag(close)
        s_txt_penn(close)
        s_txt_tdc(close)
        s_txt_over(close)
        s_subtxt_tag(close)
        s_subtxt_penn(close)
        s_subtxt_tdc(close)
        s_subtxt_over(close)
     """


####################################
# graph database
###/// incomplete
# PGA 5/17/10 replacing this with parse_db for i2b2 data
class corpus_db:
    # sent class not used yet... maybe later.
    # for now all we have stored about a sentence is its graph.
    class sent:
        def __init__(self, doc_id, sent_no):
            # stanford dependency parser graph
            # self.sdg
            self.doc_id = doc_id
            self.sent_no = sent_no
        
    def __init__(self):
        # docs is a dict with doc_id as key
        # entry is an ordered list of sentences for that doc
        self.d_docs = {}

    # graph_list is a list of dependency graphs, in order
    def add_doc(self, doc_id, graph_list):
        if self.d_docs.has_key(doc_id):
            print "error in add_doc.  Trying to reuse doc_id: %s." % doc_id

        print "add_doc: doc_id %s" % doc_id
        self.d_docs[doc_id] = graph_list

    def get_graph(self, doc_id, sent_no):
        graph_list = self.d_docs.get(doc_id)
        if debug_p:
            if self.d_docs.has_key(doc_id):
                print "get_graphs: has_key doc_id %s" % doc_id
            else:
                print "get_graphs: NO key doc_id %s" % doc_id
        # print "get_graph: graph_list: %s" % graph_list
        graph = graph_list[sent_no]
        return graph

    def get_node(self, doc_id, sent_no, token_no, word):
        graph = self.get_graph(doc_id, sent_no)
        token_id = word  + "-" + str(token_no)
        #print "get_node: type: |%s|, token_id %s" % (type(graph), token_id)
        #for key in graph.nodes.keys():
        #    print "key: %s" % key
        node = graph.nodes.get(token_id)
        return node



class STagger:

    """Wrapper for the Standford tagger.

    The model should be a file name in the tagger models subdirectory of
    self.stag_dir. The .props files contain properties of specific models
    (e.g. tagseparator). 

    chinese7.tagger
    chinese7.tagger.props
    chinese.tagger
    chinese.tagger.props
    english-bidirectional-distsim.tagger
    english-bidirectional-distsim.tagger.props
    english-caseless-left3words-distsim.tagger
    english-caseless-left3words-distsim.tagger.props
    english-left3words-distsim.tagger
    english-left3words-distsim.tagger.props
    french.tagger
    french.tagger.props
    german-dewac.tagger
    german-dewac.tagger.props
    german-fast.tagger
    german-fast.tagger.props
    german-hgc.tagger
    german-hgc.tagger.props

    st = sdp.STagger("english-caseless-left3words-distsim.tagger")

    The STagger works on Linux but does not work properly on Mac OSX. The right
    kind of string is handed in by give_input_and_end(), but when the method
    get_output_to_end() reads lines from the output pipe something is wrong with
    the encoding. In fact, the tagger itself must have gotten the wrong string
    since the tags are not correct.

    """

    def __init__(self, model):

        self.stag_dir = config.STANFORD_TAGGER_DIR
        self.mx = config.STANFORD_MX
        self.tag_separator = config.STANFORD_TAG_SEPARATOR
        self.model = model
        self.verbose = False
        #self.verbose = True

        if self.tag_separator != "":
            tag_separator_option = " -tagSeparator " + self.tag_separator + " "
        else:
            tag_separator_option = ""

        # Make the models directory explicit to fix a broken pipe error that
        # results when the entire models path is not specified. Note that
        # option: -outputFormatOptions lemmatize does not work.
        tagger_jar = self.stag_dir + "/stanford-postagger.jar:"
        maxent_tagger = 'edu.stanford.nlp.tagger.maxent.MaxentTagger'
        model = "%s/models/%s" % (self.stag_dir, self.model)
        tagcmd = "java -mx%s -cp '%s' %s -model %s%s  2>log.dat" % \
                 (self.mx, tagger_jar, maxent_tagger, model, tag_separator_option)
        if self.verbose:
            print "[stagWrapper init] \n$ %s" % tagcmd

        # create a subprocess that reads from stdin and writes to stdout
        self.proc = Popen(tagcmd, shell=True, stdin=PIPE, stdout=PIPE, universal_newlines = False)


    def tag(self, text):
        """returns a list of tagged sentence strings"""
        if self.verbose: print "[tag] text: %s" % text
        self.give_input_and_end(text)
        if self.verbose: print "[tag] after give_input_and_end"
        result = self.get_output_to_end()
        if self.verbose: print "[tag] after setting result to: %s" % result
        return result


    def give_input_and_end(self, text):
        """Passes a string to the sdp tagger subprocess. Adds a special termination
        string to use as a signal that tag output is finished."""
        terminated_line = text + u'\n~_\n'
        if self.verbose:
            print "[give_input_and_end] terminated_line: |%s|" % terminated_line
        self.proc.stdin.write(terminated_line.encode('utf-8'))
        self.proc.stdin.flush()


    def get_output_to_end(self):
        """Reads lines from the output of the subprocess (sdp parser) and returns them
        as a list of unicode strings. We use a line "~-" to signal the end of
        the output from the tagger. """

        result = []
        line = self.proc.stdout.readline()
        # Not sure why this is needed if this is called from pubmed.sh rather than 
        # fxml.test_pm() within python.  PGA
        if line is None:
            return result
        # now turn the stdout line, which is of type str, into a unicode string
        line = line.decode(sys.stdout.encoding)
        if self.verbose:
            print "[get_output_to_end] %s line is: |%s|" % (type(line).__name__, line)

        while True:
            # remove tabs from sdp output (e.g. for Phrase structure)
            line = line.strip("\n")
            line = line.lstrip()
            # The tagger will add a tag to the terminating line, so we match on
            # the first two characters only.
            if line[0:2] == "~_": 
                if self.verbose:
                    print "[get_output_to_end] found_terminator string, breaking from while loop"
                break
            if self.verbose:
                print "[get_output_to_end] in while loop"
                print "[get_output_to_end] appending line |%s|" % line
            if line != "":
                result.append(line)
            line = self.proc.stdout.readline().decode(sys.stdout.encoding)
            if self.verbose:
                print "[get_output_to_end] next %s line: |%s|" % (type(line).__name__, line)

        return result



####---------------------------------------------------

# wrapper for Standford Chinese segmenter

"""
USAGE

Unix: 
> segment.sh [-k] [ctb|pku] <filename> <encoding> <size>
  ctb : Chinese Treebank
  pku : Beijing Univ.

filename: The file you want to segment. Each line is a sentence.
encoding: UTF-8, GB18030, etc. 
(This must be a character encoding name known by Java)
size: size of the n-best list (just put '0' to print the best hypothesis
without probabilities).
-k: keep all white spaces in the input

* Sample usage: segment.sh ctb test.simp.utf8 UTF-8

* Note: Large test file requires large memory usage.  For processing 
  large data files, you may want to change memory allocation in Java 
        (e.g., to be able to use 8Gb of memory, you need to change "-mx2g" 
        to "-mx8g" inside segment.sh). Another solution is to split the test 
        file to smaller ones to reduce memory usage.
"""


class Segmenter:

    def get_config(self):
        # use defaults in config.py
        # use try/except in case some defaults are not included
        # in config.py
        #pdb.set_trace()
        try:
            self.seg_dir = config.STANFORD_SEGMENTER_DIR
        except AttributeError:
            self.sdp_dir = "."
        try:
            self.mx = config.STANFORD_MX
        except AttributeError:
            self.mx = "300m"
        try:
            self.debug_p = config.STANFORD_DEBUG_P
        except AttributeError:
            self.debug_p = 0

        global debug_p
        debug_p = 0
        
    # model should be ctb (chinese using penn term bank model)

    # eg. st = sdp.Segmenter()
    def __init__(self):
        #YZ
        self.diff=0
        
        #pdb.set_trace()
        # PGA modified to use config data
        self.get_config()
        #print "\n\ninitializing stagWrapper--init()\n"

        self.data_dir = self.seg_dir + "/data"

        # print debugging statements if True
        self.verbose = False
        #self.verbose = True

        # make the models directory explicit
        # This fixes a broken pipe error that results when the entire models path is not specified.
        # Note that option: -outputFormatOptions lemmatize  does not work.

        # One issue is to read from stdin rather than from a file.  We use the linux solution described in 
        # https://mailman.stanford.edu/pipermail/java-nlp-user/2012-July/002371.html
        # to set file to /dev/stdin

        #version used with cn_segment_file() --YZ
        #self.segcmd = ('java -mx' + self.mx + ' -cp ' + self.seg_dir + '/seg.jar edu.stanford.nlp.ie.crf.CRFClassifier -sighanCorporaDict  '  + self.data_dir + ' -testFile /dev/stdin -inputEncoding UTF-8 -sighanPostProcessing true -keepAllWhitespaces false -loadClassifier ' + self.data_dir + '/ctb.gz -serDictionary ' + self.data_dir + '/dict-chris6.ser.gz 2>log.dat' )

        #version to modify --YZ
        self.segcmd = ('java -mx' + self.mx + ' -cp ' + self.seg_dir + '/seg.jar edu.stanford.nlp.ie.crf.CRFClassifier -sighanCorporaDict  '  + self.data_dir + ' -testFile /dev/stdin -inputEncoding UTF-8 -sighanPostProcessing true -keepAllWhitespaces false -loadClassifier ' + self.data_dir + '/ctb.gz -serDictionary ' + self.data_dir + '/dict-chris6.ser.gz 2>log.dat' )
        if self.verbose:
            print "[segWrapper init]segcmd: %s" % self.segcmd

        #print "\n\n[segWrapper]before self.proc\n"
        # create a subprocess that reads from stdin and writes to stdout
        #self.proc = Popen(segcmd, shell=True, stdin=PIPE, stdout=PIPE, universal_newlines = True)
        # PGA could not get the Popen method to work, so for now doing it less efficiently with subprocess.call
        # which calls the segmenter separately for each file
        #self.proc = Popen(segcmd, shell=True, stdin=PIPE, stdout=PIPE, universal_newlines = False)

        #use Popen --YZ
        self.proc = Popen(self.segcmd, shell=True, stdin=PIPE, stdout=PIPE, universal_newlines = False)

        #print "\n\n[segWrapper]after self.proc\n"
    
    #main modifitions to make Popen work --YZ
    ######################################
    
    def seg(self, text):
            
        #YZ
        #print "txt sent in %s" %text
        self.give_input_and_end(text)
        
        #self.proc.stdout.flush()
        #print "out of sleep"
        result = self.get_output_to_end()

        #print "txt spit out %s" %result
        #print "************************"
        return(result)
    
    def is_ascii(self, s):
        
        return all(ord(c) < 128 for c in s)

    def get_output_to_end(self):

        #YZresult=[]

        line = self.proc.stdout.readline()
        while self.is_ascii(line):
            line = self.proc.stdout.readline()                                   
    
        line = line.decode(sys.stdout.encoding)
            
        return(line)
    ##################################--YZ
    
    # NOT WORKIGN for seg
    # version that expects one line of output for one line of input
    def seg_w_popoen(self, text):
        if self.verbose:
            print "[process_to_end]text: %s" % text

        self.give_input_and_end(text)
        if self.verbose:
            print "[process_to_end]after give_input_and_end"
        result = self.get_output_to_end()
        #print "[process_to_end]after setting result to: %s" % result
        return(result)

    # segmenter call that requires re-opening the segmenter for each file
    # Inefficient and slow, but at least it works!
    def cn_segment_file(self, infile, outfile):
        
        full_command = self.segcmd + ' < ' + infile + ' > ' + outfile
        if self.verbose:
            print "[seg]full_command: %s" % (full_command)

        # the arg "shell=True" allows you to enter a simple string as command.
        returncode = call(full_command, shell=True)
        #print "returncode: %s" % returncode

    # version without special terminator marker added.
    # passes a string to the sdp tagger subprocess
    # Also passes a special "~" string to use as a signal that tag output
    # is finished.
    def give_input_and_end(self,text):
        terminated_line = text
        if self.verbose:
            print "[give_input_and_end]terminated_line: |%s|" % terminated_line
            
        self.proc.stdin.write(terminated_line.encode('utf-8'))

        if self.verbose:
            print "[give_input_and_end]After proc.stdin.write"
        
        self.proc.stdin.flush()
        self.proc.stdin.write('\n')
        self.proc.stdin.write('\n')

    # Reads lines from the output of the subprocess (sdp parser) and 
    # concatenates them into a single string, returned as the result
    # We use a line with a single "~" to signal the end of the output
    # from the tagger.  Note that the tagger will add _<tag> to the tilda,
    # so we match on the first two characters only for the termination condition.
    def get_output_to_end_old(self):
        ###print "[get_output] entered..."
        result=[]
        #line = self.proc.stdout.readline()
        line = self.proc.stdout.readline().decode('utf8')
        #line = self.proc.stdout.readline()
        
        # Not sure why the != None is needed if this is called from pubmed.sh rather than 
        #  fxml.test_pm() within python.  PGA
        if line != None:
            line = line.decode(sys.stdout.encoding)
            
        #line = self.proc.stdout.readline()
        ###line = unicode(line)
        #print "[tag: get_output_to_end]line is: |%s|" % line

        # remove tabs from sdp output (e.g. for Phrase structure)
        line = line.strip("\n")
        #line = line.lstrip()

        if self.verbose:
            print "[get_output_to_end]in while loop.  line: |%s|" % line
        #result=result+line
        # Append result only if line is not empty
        if line != "":
            result.append(line)
        if self.verbose:
            print "[get_output_to_end]result: |%s|" % result
        #line = self.proc.stdout.readline()
        #line = self.proc.stdout.readline().decode('utf8')
        line = self.proc.stdout.readline().decode(sys.stdout.encoding)
        ###line = unicode(line)
        if self.verbose:
            print "[get_output_to_end]next line: |%s|" % line

        if self.verbose:
            print "[get_output_to_end]Out of loop.  Returning..."

        return(result)


    def test1(self):

        print "sentence 1\n"

        result = self.process_to_end('John went today. Second sentence exists.')
        #self.give_input_and_end('John went to school today.')
        #result = self.get_output_to_end()
        print "result: %s" % result
        
        print "sentence 2\n"
        
        result = self.process_to_end('Mary went to school yesterday. Another sentence occurs!')
        #self.give_input('Mary went to school yesterday. Another sentence occurs!')
        #result = self.get_output()
        print "result: %s" % result

        print "sentence 3\n"

        result = self.process_to_end('John went today. Repeated sent 1.')
        #self.give_input_and_end('John went to school today.')
        #result = self.get_output_to_end()
        print "result: %s" % result




################################################################
# wrapper for subprocess test

class sp:

    # model should be a file name in the tagger models subdirectory 
    def __init__(self):

        #tagcmd = ('echo ' + ' 2>log.dat')
        tagcmd = ('echo ')

        print "[sp init]tagcmd: %s" % tagcmd

        # create a subprocess that reads from stdin and writes to stdout
        self.proc = Popen(tagcmd, shell=True, stdin=PIPE, stdout=PIPE, universal_newlines = True)

    def process_to_end(self, text):
        self.give_input_and_end(text)
        return self.get_output_to_end()
        #return self.get_outputs()
            
    # passes a string to the sdp parser subprocess
    def give_input(self,text):
        #self.proc.stdin.flush()
        self.proc.stdin.write(text+'\n')
        self.proc.stdin.flush()

    # passes a string to the sdp tagger subprocess
    # Also passes a special "~" string to use as a signal that parse output
    # is finished.
    def give_input_and_end(self,text):
        #self.proc.stdin.flush()
        self.proc.stdin.write(text+'\n~\n')
        self.proc.stdin.flush()


    # Reads lines from the output of the subprocess (sdp parser) and 
    # concatenates them into a single string, returned as the result
    def get_output_to_end(self):
        ###print "[get_output] entered..."
        result=""
        line = self.proc.stdout.readline()
        line = unicode(line)
        #while len(line)>2 :
        while line != "~\n":

            line = line.strip("\n")
            #result=result+line
            # remove tabs from sdp output (e.g. for Phrase structure)
            line = line.lstrip()
            result=result + "\t" + line
            ###print "[get_output]result: %s" % result
            line = self.proc.stdout.readline()
            line = unicode(line)

        return result[1:]

class Sent:

    # e.g. 'John_NNP went_VBD today_NN ._.'
    def __init__(self, tag_string, chunk_schema):
        self.debug = False
        #self.debug = True
        self.tag_string = tag_string
        self.len = 0
        self.last = 0
        self.sentence = ""
        self.toks = []
        self.tags = []

        # chart is a sequence of chunk instances, one for each token
        self.chart = []
        self.init_chart(tag_string)
        self.chunk_chart_tech(chunk_schema)

    # create initial chart using raw token list
    def init_chart(self, tag_string):
        if self.debug:
            print "[init_chart]tag_string: %s" % tag_string
        self.tags = tag_string.split(" ")
        self.len = len(self.tags)
        self.last = self.len - 1
        l_tok = []
        index = 0
        next = 1
        for tag in self.tags:
            # use rsplit with maxsplit = 1 so that we don't further split tokens like CRF07_BC
            (tok, tag) = tag.rsplit("_", 1)
            chunk = Chunk(index, next, tok, tag)
            self.chart.append(chunk)
            l_tok.append(tok)
            index += 1
            next += 1
        # create the sentence
        self.sentence = " ".join(l_tok)
        self.toks = l_tok



    # fill out phrasal chunks in the chart
    # This uses the patterns in the chunk_schema to combine tokens into a chunk
    # The chunk must end in certain toks, so we keep track of the last legal end token
    # and if it differs from the actual end token (such as a conjunction or adjective),
    # we create the chunk up to the last legal end token.
    def chunk_chart_tech(self, chunk_schema):


        # True when we are inside of a chunk
        # used to know if we should continue chunking based on
        # start chunk constraints or continue chunk constraints.
        inChunk_p = False
        
        """
        # These flags are language dependent!  Probably better to identify head terms
        # after chunks are created"
        # ENGLISH:
        # Has the dominant head term been located?
        # This would be an ing-verb followed by a determiner or a noun followed by prep or end
        # NOTE that conjunctions raise issues.
        head_found_p = False
        # If there is a modifying phrase (e.g., introduced by "of"), then look for its head term
        mod_head_found_p = False
        """

        #print "[Sent chunk]%s" % self.chart
        # last tag
        last_tag = " "

        # start index of current chunk
        cstart = 0

        # index of the last legal end token for a chunk
        last_legal_end_index = -1
        last_legal_phrase = ""
        # list of tags in a chunk
        last_legal_chunk_tags = []

        if self.debug:
            print "[chunk_chart]self.len: %i" % self.len
        for i in range(self.len):
            if self.debug:
                print "[chunk_chart]i: %i" % i

            chunk = self.chart[i]
            # check if chunk has same tag group as previous token
            if self.chunkable_p(chunk, inChunk_p, chunk_schema):
                # If this token starts a chunk, advance cstart to this token.
                # Otherwise cstart should already be the index of the first token in this chunk.
                if not inChunk_p:
                    cstart = i
                # extend the start chunk by concatenating the current token to the 
                # chunk token stored at the start index of the chunk.
                self.chart[cstart].chunk_end = i + 1
                ### //// need to determine the actual head  PGA
                #self.chart[cstart].head = chunk.tok


                if self.debug:
                    print "chunk phrase: |%s|, start: %i" % (self.chart[cstart].phrase, cstart)
                if not inChunk_p:
                    # set the label for the first element in the chunk to "tech"
                    self.chart[cstart].label = "tech"
                else:
                    # extend the phrase
                    self.chart[cstart].phrase = self.chart[cstart].phrase + " " + chunk.tok
                    self.chart[cstart].chunk_tags.append(chunk.tag)

                inChunk_p = True
                # check if this token could be a legal end
                if self.legal_end_p(chunk, chunk_schema):
                    last_legal_end_index = i
                    # update the last legal phrase
                    last_legal_phrase = self.chart[cstart].phrase
                    last_legal_chunk_tags.append(chunk.tag)
            else:
                # terminate chunk
                # make sure the phrase and index correspond to the last legal end
                # We'll throw away any tokens up to the last legal ending of a chunk.
                if last_legal_end_index > -1:
                    self.chart[cstart].phrase = last_legal_phrase
                    self.chart[cstart].chunk_tags = last_legal_chunk_tags
                    self.chart[cstart].chunk_end = last_legal_end_index + 1
                else:
                    # reset the start chunk to remove all (now invalidated) phrasal info
                    self.chart[cstart].label = ""
                    self.chart[cstart].chunk_end = self.chart[cstart].tok_end + 1
                    self.chart[cstart].phrase = self.chart[cstart].tok
                    self.chart[cstart].chunk_tags = []

                last_legal_end_index = -1
                cstart = i
                inChunk_p = False

    def legal_end_p(self, chunk, chunk_schema):
        # return True if this token can legally end a chunk
        try:
            if debug_p:
                print "[legal_end_p]in chunk, tok: %s" % chunk.tok
            pat = chunk_schema.d_end[chunk.tag]
            
            # check constraints
            if debug_p:
                print "[legal_end_p]pat: %s, tag: %s" % (pat, chunk.tag)
            test_val = False
            if pat != []:
                if pat[0] == "-" and chunk.tok.lower() not in pat[1:]:
                    test_val == True
                else:
                    test_val == False
                if debug_p:
                    print "[legal_end_p](pat[0] == - and chunk.tok.lower() not in pat[1:]): %r" % (test_val)
            if (pat == []) or (pat[0] == "-" and chunk.tok.lower() not in pat[1:]) or (pat[0] == "+" and chunk.tok.lower() in pat[1:]):
                if debug_p:
                    print "[legal_end_p] matched!"
                return True
            else:
                return False
        except KeyError:
            return False





        
    # returns True if the current token/tag is part of a chunk according to
    # the patterns stored in chunk_schema and the current state (either in a
    # chunk or not).
    def chunkable_p(self, chunk, inChunk_p, chunk_schema):
        # match the chunk pattern depending on whether starting or
        # continuing a chunk
        # If the tag is not in our pattern, then return false
        debug_p = False
        try:
            if inChunk_p:
                if debug_p:
                    print "[chunkable]in chunk, tok: %s" % chunk.tok
                pat = chunk_schema.d_cont[chunk.tag]
            else:
                if debug_p:
                    print "[chunkable]NOT yet in chunk, tok: %s" % chunk.tok
                pat = chunk_schema.d_start[chunk.tag]

            # check constraints
            if debug_p:
                print "[chunkable_p]pat: %s, inChunk_p: %s, tag: %s" % (pat, inChunk_p, chunk.tag)
            test_val = False
            if pat != []:
                if pat[0] == "-" and chunk.tok.lower() not in pat[1:]:
                    test_val == True
                else:
                    test_val == False
                if debug_p:
                    print "[chunkable_p](pat[0] == - and chunk.tok.lower() not in pat[1:]): %r" % (test_val)
            if (pat == []) or (pat[0] == "-" and chunk.tok.lower() not in pat[1:]) or (pat[0] == "+" and chunk.tok.lower() in pat[1:]):
                if debug_p:
                    print "[chunkable_p] matched!"
                return True
            else:
                return False
        except KeyError:
            return False
        
    """
    # fill out phrasal chunks in the chart
    def chunk_chart_generic(self):
        #print "[Sent chunk]%s" % self.chart
        # last tag
        last_tag = " "

        # start index of current chunk
        cstart = 0

        if self.debug:
            print "[chunk_chart]self.len: %i" % self.len
        for i in range(self.len):
            if self.debug:
                print "[chunk_chart]i: %i" % i

            chunk = self.chart[i]
            # check if chunk has same tag group as previous token
            if last_tag[0] == chunk.tag[0]:
                # extend the start chunk by concatenating the current token to the 
                # chunk token stored at the start index of the chunk.
                self.chart[cstart].chunk_end = i + 1
                self.chart[cstart].head = chunk.tok
                self.chart[cstart].phrase = self.chart[cstart].phrase + " " + chunk.tok
                if self.debug:
                    print "chunk phrase: |%s|" % self.chart[cstart].phrase
            else:
                # terminate chunk
                last_tag = chunk.tag
                cstart = i
       
    """

    def __display__(self):
        print "[Sent] %s" % self.tag_string
        for chunk in self.chart:
            chunk.__display__()

    # return sentence with square brackets around the chunk starting at index
    def highlight_chunk(self, index):
        l_tok = self.toks
        last_tok = self.chart[index].chunk_end - 1
        l_highlight = []
        i = 0
        for tok in l_tok:
            if i == index:
                l_highlight.append("[")
            l_highlight.append(tok)
            if i == last_tok:
                l_highlight.append("]")
            i += 1

        hsent = " ".join(l_highlight)
        return(hsent)
    
    def chunk_iter(self):
        chunk = self.chart[0]
        while True:
            #chunk.__display__()
            yield(chunk)
            if chunk.chunk_end < self.len:
                #print "[chunk_iter]chunk_end: %i" % chunk.chunk_end
                chunk = self.chart[chunk.chunk_end]
            else:
                #print "[chunk_iter before break]chunk_end: %i" % chunk.chunk_end
                break

    # returns the string of up to count tokens prior to index
    def prev_n(self, index, count):
        prev_n_string = ""
        start = index - count
        if start < 0:
            start = 0
        
        i = start
        while i < index:
            prev_n_string = prev_n_string + " " + self.chart[i].tok
            i += 1
        return(prev_n_string)

    def next_n(self, index, count):
        next_n_string = ""
        end = index + count
        if end >= self.len:
            end = self.len
        
        i = index
        while i < end:
            next_n_string = next_n_string + " " + self.chart[i].tok
            i += 1
        return(next_n_string)

    # previous verb
    # return closest verb to left of NP
    # as well as prep or particle if there is one after verb
    def prev_V(self, index):
        verb = ""
        prep = ""
        verb_prep = ""
        i = index -1
        while i > 0:
            # terminate if verb is found
            if self.chart[i].tag[0] == "V":
                verb = self.chart[i].tok
                break
            # terminate if a noun is reached before a verb
            if self.chart[i].tag[0] == "N":
                break
            # keep a prep if reached before verb
            if self.chart[i].tag[0] in ["RP", "IN"]:
                prep = self.chart[i].tok
            else:
                # keep looking 
                i = i - 1
        if verb != "":
            verb_prep = verb + " " + prep
        return(verb_prep)

    # previous adj (JJ, JJR, JJS)
    # Adj must be immediately bfore index term
    def prev_J(self, index):
        i = index - 1
        if self.chart[i].tag[0] == "J":
            return(self.chart[i].tok)
        else:
            return("")

    def head_N(self, index):
        if self.chart[index].tag[0] != "N":
            return("")
        else:
            head_index = self.chart[index].chunk_end - 1
            return(self.chart[head_index].tok)

# unfinished
class Chunk:
    
    def __init__(self, tok_start, tok_end, tok, tag ):
        self.tok_start = tok_start
        self.tok_end = tok_end
        self.tok = tok
        self.tag = tag
        # label is changed if a chunk pattern is matched
        self.label = tag
        # if not a multi-token chunk, chunk_start/end should be same as
        # tok_start/end
        self.chunk_start = tok_start
        self.chunk_end = tok_end
        self.head = ""
        self.of_head = ""
        self.phrase = tok
        # list of strings 
        self.tokens = []
        self.premods = []
        self.postmod = None  # connector + NOMP
        self.precontext = []
        self.postcontext = []
        # list of tags in a phrasal chunk
        self.chunk_tags = []
        # for head idx, -1 means no head found
        self.head_idx = -1
        self.prep_head_idx = -1

    def head_idx(self):
        idx = self.tok_start
        head_idx = idx
        l_tags = self.chunk_tags
        for tag in l_tags:

            # check for termination conditions
            if tag in ["IN", "DT", "CC"]:
                break
            else:
                head_idx = idx    
            idx += 1

        # for debugging, print the idx within the phrase, rather than within the sentence
        rel_idx = head_idx - self.tok_start
        print "[head_idex]rel_idx: %i" % rel_idx
        return(idx)

    # return the index of the head of a prep phrase, if there is one.  If not
    # return -1.
    def prep_head_idx(self):
        idx = self.tok_start
        head_idx = -1
        l_tags = self.chunk_tags
        prep_found_p = False
        nv_found_p = False
        for tag in l_tags:

            if prep_found_p == True:
                # check for termination conditions
                if tag in ["IN"]:
                    break
                else:
                    if tag[0] == "N" or tag[0] == "V":
                        head_idx = idx    
                        nv_found_p = True
            # is the tag a prep?
            if tag == "IN":
                prep_found_p = True
            idx += 1

        # for debugging, print the idx within the phrase, rather than within the sentence
        rel_idx = head_idx - self.tok_start
        print "[prep_head_idx]rel_idx: %i" % rel_idx
        return(idx)
            

    def __display__(self):
        print "Chunk type: %s, phrase: %s, %i, %i" % (self.tag, self.phrase, self.chunk_start, self.chunk_end)

# instance of a chunk definition in the form of two dictionaries:
# conditions for matching the start of a chunk (tags + token constraints)
# conditions for continuing a chunk (tags + token constraints)
class chunkSchema:
    
    def __init__(self, start_pat, cont_pat, end_pat):
        self.d_start = {}
        self.d_cont = {}
        self.d_end = {}
        for pat in start_pat:
            key = pat[0]
            value = pat[1]
            self.d_start[key] = value
        for pat in cont_pat:
            key = pat[0]
            value = pat[1]
            self.d_cont[key] = value
        for pat in end_pat:
            key = pat[0]
            value = pat[1]
            self.d_end[key] = value


# constraints are indicated by 
# "-" none of the following strings
# "+" only the following strings
# [] no constraints
# end_pat are the legal POS that can end a chunk
def chunker_tech ():
    both_pat =  [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []], ["POS", []],  ["JJ", ["-", "further", "such", "therebetween", "same", "following"] ], ["JJR", [] ], ["JJS", [] ], ["FW", [] ], ["VBG", ["-", "describing", "improving", "using", "employing",  "according", "resulting", "having", "following", "including", "containing", "consisting", "disclosing"]  ] ] 
    #start_pat = [ ["NN", ["-", "method"]] ] 
    start_pat = []
    cont_pat = [ ["NN", []], ["VBN", []], ["IN", ["+", "of"]], ["DT",  []], ["CC", []] ]
    end_pat = [ ["NN", []], ["NNP", []], ["NNS", []], ["NNPS", []], ["VBG", ["-", "describing", "improving", "using", "employing", "according", "resulting", "having", "following", "including", "containing", "consisting", "disclosing"]  ] ]
    start_pat.extend(both_pat)
    cont_pat.extend(both_pat)
    cs = chunkSchema(start_pat, cont_pat, end_pat)
    return(cs)

# tag and output data for a sentence (for testing)
def test_sent(sentence):

    
    # create a chunker schema instance
    cs = chunker_tech()

    st = STagger("english-caseless-left3words-distsim.tagger") 
    s1 = Sent(st.tag(sentence)[0], cs)
    s1.__display__()
    #print "ncontext:"
    #s1.ncontext()

    # collect N contexts
    i = 0
    for chunk in s1.chunk_iter():
        if chunk.label == "tech":
            verb = s1.prev_V(i)
            adj =  s1.prev_J(i)
            head = s1.head_N(i)
            hsent = s1.highlight_chunk(i)
            print "index: %i, start: %i, end: %i, sentence: %s" % (i, chunk.chunk_start, chunk.chunk_end, s1.sentence)
            print "%s\t%s\t%s\t%s\t%s\t%s" % (chunk.phrase,  verb, adj, s1.prev_n(chunk.chunk_start, 3), s1.next_n(chunk.chunk_end, 3), hsent)
            print ""
        i = chunk.chunk_end
    return(s1)



