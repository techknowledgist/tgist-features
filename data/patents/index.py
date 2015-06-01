"""

Some utilities to deal with merging indexes and extracting information from
indexes.

Just for CN patents. There are a few test and analyze methods available. Some of
them take a long time (not hours though but minutes), results are indicated
below in the listing of the methods.

test_reading():
    Reads one line from each of the four files
    
analyze_short_ids():
    Loads all data from the ID2DOMAIN file and checks whether all ids are digits
    only. They are not. Out of 5,962,693 total ids there are 468,921 ids with
    non-digits. Those are either ids like 2004/0134979 (47,644), or they are ids
    that start with D (395,601), H (966), PP (15,400) or RE (9,310).

analyze_domains():
    Rounds up all domains and prints a count for each. partially intended to see
    if funny stuff is going on when getting the domain. Running this gives the
    expected domains (A41-A50 and nil), counts vary from 93,431 (A45) 916,0072
    (A41), there are 2,568,645 ids that are not mapped to a domain.

analyze_id_mapping():
    Checks the overlap between short identifiers and converted long
    identifiers. This revealed that there is almost no overlap so we have a
    problem.

get_domain_file_lists():
    Create the domain file lists by combining information from various
    list. This is now broken or needs to be run on a machine with much more
    memory. In fact, it is useless till the identifier problem is solved.

"""

import os, sys, glob

DATA1 = '/home/j/corpuswork/fuse/FUSEData/lists'
DATA2 = '/home/j/corpuswork/fuse/FUSEData/2014-09-23/lists'
DATA3 = '.'


# long-identifier (CN85100490A) TAB full-path
# over patents from 2013 data drop 
ID2PATH = os.path.join(DATA1, 'ln_cn.all.ordered.txt')

# application-date TAB publication-date TAB full-path
# over patents from 2013 data drop and 2014 data drop
DATES2PATH_2013 = os.path.join(DATA1, 'ln_cn.all.index.date2path.txt')
DATES2PATH_2014 = os.path.join(DATA2, 'lncn-date-idx.txt')

# short-identifier (5466294) COMMA year COMMA domain
# over some set of patents from MITRE
# this is a directory, files in there match lnusp-patent-documents-*.csv
# this turns out to be useless because it is using BAE-internal identifiers
ID2DOMAIN = os.path.join(DATA1, "patentsByGtf") 

# full-path TAB domains
PATH2DOMAINS_2013 = os.path.join(DATA3, 'lncn-2013-idx-domain.txt')
PATH2DOMAINS_2014 = os.path.join(DATA3, 'lncn-2014-idx-domain.txt')

# IPC codes from MITRE
IPC_CODES =  os.path.join(DATA3, 'ipc-codes.txt')


## READING DATA

def read_ID2PATH(test=False, max=None, verbose=True):
    if verbose:
        print "Reading", ID2PATH
    idx = {}
    count = 0
    for line in open(ID2PATH):
        count += 1
        if count % 100000 == 0 and verbose: print '  ', count
        if max is not None and count > max: break
        (id, path) = line.strip().split()
        idx[id] = path
        if test: return idx
    return idx

def read_DATES2PATH_2013(test=False, max=None,verbose=True):
    if verbose:
        print "Reading", DATES2PATH_2013
    idx = {}
    count = 0
    for line in open(DATES2PATH_2013):
        count += 1
        if count % 100000 == 0 and verbose: print '  ', count
        if max is not None and count > max: break
        (appdate, pubdate, path) = line.strip().split()
        idx[path] = [appdate, pubdate]
        if test: return idx
    return idx

def read_ID2DOMAIN(test=False, max=None, verbose=True):
    if verbose:
        print "Reading", ID2DOMAIN
    idx = {}
    count = 0
    for fname in glob.glob(ID2DOMAIN + "/lnusp-patent-documents-*.csv"):
        for line in open(fname):
            if line.find('LNUSP') > -1:
                continue
            count += 1
            if count % 100000 == 0 and verbose: print '  ', count
            if max is not None and count > max: break
            # note that the domain is either 'null' or something like
            # 'LNCN-PC-T-A41-V01'
            (id, year, domain) = line.strip().split(',')
            domain = get_domain(domain)
            idx[id] = [year, domain]
            if test: return idx
    return idx

def read_DATES2PATH_2014(test=False, max=None, verbose=True):
    if verbose:
        print "Reading", DATES2PATH_2014
    idx = {}
    count = 0
    for line in open(DATES2PATH_2014):
        count += 1
        if count % 100000 == 0 and verbose: print '  ', count
        if max is not None and count > max: break
        (appdate, pubdate, path) = line.strip().split()
        idx[path] = [appdate, pubdate]
        if test: return idx
    return idx


## DOMAINS

class IPCcodes(object):

    def __init__(self):
        """Creates a dictionary of classname to domain mappings, where
        classnames look like G06, F24 and H01Q and domains like A46."""
        self.codes = {}
        domain = None
        for line in open(IPC_CODES):
            line = line.strip("\n ")
            if not line or line[0] == '#':
                continue
            if line[0] == 'A':
                domain = line.split()[0]
            elif line[0] == "\t":
                classname = line.split()[0]
                self.codes[classname] = domain
                print domain, classname

    def get_domain(self, classname):
        """The classname handed in here is something like A-47-J (section,
        class, subclass), so we glue the parts together and look whether the
        dictionary has the 3-part or 2-part classname. Returns a pair of the
        actual key and the domain."""
        subs = classname.split('-')
        sc = ''.join(subs[:2])   # section, class
        scsc = ''.join(subs) # section, class, subclass        
        if self.codes.has_key(sc):
            return sc, self.codes[sc]
        return scsc, self.codes.get(scsc, None)


## UTILITIES

def get_domain(domain_string):
    if domain_string == 'null': return 'nil'
    return domain_string.split('-')[3]

def shorten_id(id):
    """Take a long id and turn it into the short id as used by the MITRE domain
    list. Remove the leading 'CN' and trailing letter, which would be one of A,
    B, C, U and Y. Leaves the RE, D, PP etcetera in the beginning. Does not
    remove A8 or K1 at the end, not sure what to do with those but they are very
    rare (1 and 28 occurrences respectively)."""
    if id.startswith('CN'):
        id = id[2:]
    if not id[-1].isdigit():
        id = id[:-1]
    return id

def get_id_from_path(path):
    """Get the long identifier from the path."""
    id = os.path.basename(path)
    if id.endswith('.xml'):
        id = id[:-4]
    return id


    
## TOP-LEVEL FUNCTIONALITY

def test_reading():
    print
    for name, fun in [('ID2PATH      ', read_ID2PATH),
                      ('ID2DOMAIN    ', read_ID2DOMAIN),
                      ('PATH2DATES   ', read_DATES2PATH_2013),
                      ('PATH2DATES_UP', read_DATES2PATH_2014)]:
        idx = fun(test=True, verbose=False)
        print "%-12s" % name, idx
    print
    
def analyze_short_ids():
    idx = read_ID2DOMAIN()
    print len(idx)
    #for (k,v) in idx.items(): print k, v
    non_digits = 0
    for id in idx:
        if not id.isdigit():
            non_digits += 1
    print non_digits

def analyze_domains():
    idx = read_ID2DOMAIN()
    domains = {}
    for id in idx:
        domain = idx[id][1]
        domains[domain] = domains.get(domain,0) + 1
    for domain in sorted(domains.keys()):
        print domain, domains[domain]

def analyze_id_mapping():
    idx_short_ids = read_ID2DOMAIN()
    idx_long_ids = read_ID2PATH()
    #print idx_short_ids.keys()
    has_mapping = 0
    no_mapping = 0
    for lid in idx_long_ids.keys():
        sid = shorten_id(lid)
        #print lid, sid, idx_short_ids.has_key(sid)
        if idx_short_ids.has_key(sid):
            has_mapping += 1
        else:
            no_mapping += 1
    print has_mapping, no_mapping
    
        
def get_domain_file_lists():
    ipc_codes = IPCcodes()
    print ipc_codes.get_domain('C-12-M')
    print ipc_codes.get_domain('B-27-M')
    print ipc_codes.get_domain('X-27-M')

    path2dates2014 = read_DATES2PATH_2014(max=10)
    c = 0
    for line in open(PATH2DOMAINS_2014):
        c += 1
        if c > 10: break
        path, classnames = line.rstrip("\n\r\f").split("\t")
        domains = {}
        for classname in classnames.split():
            name, domain = ipc_codes.get_domain(classname)
            if domain is not None:
                domains[domain] = True
        print path, path2dates2014[path][0][:4], domains.keys()
    return

    id2path = read_ID2PATH(max=1000000000)
    id2domain = read_ID2DOMAIN(max=100000000)
    path2dates = read_DATES2PATH_2013(max=1000000000)
    path2dates2 = read_DATES2PATH_2014(max=1000000000)
    print len(id2path)
    print len(id2domain)
    print len(path2dates)
    print len(path2dates2)
    idx = Index()
    for longid, path in id2path.items():
        idx.add_longid_path(longid, path)
    for shortid, year_and_domain in id2domain.items():
        year = year_and_domain[0]
        domain = year_and_domain[1]
        idx.add_shortid_year_domain(shortid, year, domain)
    for path, dates in path2dates.items():
        idx.add_path_appdate_pubdate(path, dates[0], dates[1])
    for path, dates in path2dates2.items():
        idx.add_path_appdate_pubdate(path, dates[0], dates[1])
    idx.export_domains()
    #idx.pp(open('tmp-index.txt', 'w'))
    

class Index(object):

    def __init__(self):
        self.data = {}

    def pp(self, fh=sys.stdin):
        for shortid in sorted(self.data.keys()):
            for longid in sorted(self.data[shortid].keys()):
                ie = self.data[shortid][longid]
                fh.write("%s\n" % ie)

    def get(self, shortid, longid):
        if not self.data.has_key(shortid):
            self.data[shortid] = { longid: IndexElement(shortid, longid) }
            return self.data[shortid][longid]
        if not self.data[shortid].has_key(longid):
            self.data[shortid][longid] = IndexElement(shortid, longid)
        return self.data[shortid][longid]

    def add_longid_path(self, longid, path):
        shortid = shorten_id(longid)
        ie = self.get(shortid, longid)
        ie.set_path(path)

    def add_shortid_year_domain(self, shortid, year, domain):
        ie = self.get(shortid, None)
        ie.set_year(year)
        ie.set_domain(domain)

    def add_path_appdate_pubdate(self, path, appdate, pubdate):
        longid = get_id_from_path(path)
        shortid = shorten_id(longid)
        #print path, shortid, longid
        ie = self.get(shortid, longid)
        ie.set_path(path)
        ie.set_appdate(appdate)
        ie.set_pubdate(pubdate)

    def export_domains(self):
        for shortid, dict in self.data.items():
            keys = dict.keys()
            if None in keys and len(keys) > 1:
                print keys


        
class IndexElement(object):

    def __init__(self, shortid, longid):
        if shortid== '.xm':
            1/0
        self.short_id = shortid
        self.long_id = longid
        self.year = None
        self.appdate = None
        self.pubdate = None
        self.path = None
        self.domain = None

    def __str__(self):
        return "<IndexElement sid=%s lid=%s year=%s app=%s pub=%s domain=%s>" \
               % (self.short_id, self.long_id, self.year,
                  self.appdate, self.pubdate, self.domain)

    def set_long_id(self, longid):
        if self.long_id and self.long_id != longid:
            print "WARNING: inconsistent long identifiers"
            print self, longid
        else:
            self.long_id = longid
            
    def set_path(self, path):
        if self.path is not None and self.path != path:
            # A version is larger than the B version
            if self.path[-5] == 'B' and path[-5] == 'A':
                self.path = path
            if self.path[-5] == 'A' and path[-5] == 'B':
                pass
            else:
                print "WARNING: inconsistent paths"
                print self
                print '  OLD PATH', self.path, os.path.getsize(self.path)
                print '  NEW PATH', path, os.path.getsize(path)
        else:
            self.path = path
        
    def set_year(self, year):
        if self.year:
            print "WARNING: already have year"
        self.year = year
        
    def set_domain(self, domain):
        if self.domain:
            print "WARNING: already have domain"
        self.domain = domain
        
    def set_appdate(self, date):
        if self.appdate:
            print "WARNING: already have appdate"
        self.appdate = date
        
    def set_pubdate(self, date):
        if self.pubdate:
            print "WARNING: already have pubdate"
        self.pubdate = date
    
        
if __name__ == '__main__':

    test_reading()
    #analyze_short_ids()
    #analyze_domains()
    #analyze_id_mapping()
    
    get_domain_file_lists()
