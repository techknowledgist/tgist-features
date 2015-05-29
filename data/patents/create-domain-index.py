"""

Create a domain index for LNCN documents.

Extracts the section, class and subclass from the following tags:

<classification-ipcr sequence="2">
    <section>H</section>
    <class>04</class>
    <subclass>L</subclass>
</classification-ipcr>

Instead of classification-ipcr, the tag could also be classification-ipc.

"""



import os, sys, codecs, time

DATA1 = '/home/j/corpuswork/fuse/FUSEData/lists'
DATA2 = '/home/j/corpuswork/fuse/FUSEData/2014-09-23/lists'

# long-identifier (CN85100490A) TAB full-path
# over patents from 2013 data drop 
ID2PATH_2013 = os.path.join(DATA1, 'ln_cn.all.ordered.txt')

# full-path
# over new patents from 2014 data drop only
PATH_2014 = os.path.join(DATA2, 'lncn-paths.txt')


def extract_domains(fname, out, log):
    #print fname
    fh = codecs.open(fname, encoding='utf8')
    in_classification_ipc = False
    in_classification_ipcr = False
    domains = []
    section, classname, subclass = None, None, None
    for line in fh:
        line = line.strip()
        if line.startswith('<classification-ipcr '):
            in_classification_ipcr = True
            section, classname, subclass = None, None, None
        elif line.startswith('</classification-ipcr'):
            in_classification_ipcr = False
            domains.append([section, classname, subclass])
        elif line.startswith('<classification-ipc '):
            in_classification_ipc = True
            section, classname, subclass = None, None, None
        elif line.startswith('</classification-ipc'):
            in_classification_ipc = False
            domains.append([section, classname, subclass])
        elif in_classification_ipcr or in_classification_ipc:
            if line.startswith('<section>'):
                section = get_value(line)
            elif line.startswith('<class>'):
                classname = get_value(line)
            elif line.startswith('<subclass>'):
                subclass = get_value(line)
        elif line.startswith('</bibliographic-data>'):
            break
    domain_strings = {}
    for domain in domains:
        if None in domain:
            log.write("WARNING - incomplete domain %s for %s\n" % (domain, fname))
        else:
            domain_strings['-'.join(domain)] = True
    out.write("%s\t%s\n" % (fname, ' '.join(domain_strings.keys())))
    fh.close()
    
def get_value(line):
    return line.split('>')[1].split('<')[0]

def extract_domains_2013():
    print "Creating lncn-2013-idx-domain.txt"
    count = 0
    out = open("lncn-2013-idx-domain.txt", 'w')
    log = open("lncn-2013-idx-domain.log", 'w')
    for line in open(ID2PATH_2013):
        count += 1
        if count % 10000 == 0:
            log.write("%d %s\n" % (count, time.strftime("%x %X")))
            log.flush()
        #if count > 1000: break
        fname = line.strip().split("\t")[1]
        extract_domains(fname, out, log)

def extract_domains_2014():
    print "Creating lncn-2014-idx-domain.txt"
    count = 0
    out = open("lncn-2014-idx-domain.txt", 'w')
    log = open("lncn-2014-idx-domain.log", 'w')
    for line in open(PATH_2014):
        count += 1
        if count % 10000 == 0: 
            log.write("%d %s\n" % (count, time.strftime("%x %X")))
            log.flush()
        #if count > 1000: break
        fname = line.strip()
        extract_domains(fname, out, log)


if __name__ == '__main__':

    if sys.argv[1] == '2013': extract_domains_2013()
    if sys.argv[1] == '2014': extract_domains_2014()
