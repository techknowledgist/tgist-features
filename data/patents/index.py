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

idx_years_domains(date_reader, domain_file, output, max=sys.maxint):
    Combine the information from the date index and the domain index. When you
    run these for 2013 and 2014 and concatenate the results, you will get a file
    (full-path TAB year TAB domain) with 133-534k patents for the domains (3.3M
    have None, no domain).

create_file_lists():
    Create file lists for all domains and for all years.
    
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

# full-path TAB domains
PATH2DOMAINS_2013 = os.path.join(DATA3, 'lncn-2013-idx-domain.txt')
PATH2DOMAINS_2014 = os.path.join(DATA3, 'lncn-2014-idx-domain.txt')

# IPC codes from MITRE
IPC_CODES = os.path.join(DATA3, 'ipc-codes.txt')

# full-path TAB year TAB domain
# these are created by this script
YEARS_AND_DOMAINS_2013 = os.path.join(DATA3, 'lncn-2013-idx-year-domain.txt')
YEARS_AND_DOMAINS_2014 = os.path.join(DATA3, 'lncn-2014-idx-year-domain.txt')
YEARS_AND_DOMAINS_ALL = os.path.join(DATA3, 'lncn-all-idx-year-domain.txt')

# short-identifier (5466294) COMMA year COMMA domain
# over some set of patents from MITRE
# this is a directory, files in there match lnusp-patent-documents-*.csv
# this turns out to be useless because it is using BAE-internal identifiers
ID2DOMAIN = os.path.join(DATA1, "patentsByGtf") 


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

def read_DATES2PATH_2013(max=None, verbose=True):
    return read_DATES2PATH(DATES2PATH_2013, max, verbose)

def read_DATES2PATH_2014(max=None, verbose=True):
    return read_DATES2PATH(DATES2PATH_2014, max, verbose)

def read_DATES2PATH(fname, max=None, verbose=True):
    if verbose:
        print "Reading", fname
    idx = {}
    count = 0
    for line in open(fname):
        count += 1
        if count % 100000 == 0 and verbose: print '  ', count
        if max is not None and count > max: break
        (appdate, pubdate, path) = line.strip().split()
        idx[path] = [appdate, pubdate]
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
                #print domain, classname

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

    def test(self):
        print self.get_domain('C-12-M')
        print self.get_domain('B-27-M')
        print self.get_domain('X-27-M')


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
        idx = fun(max=1, verbose=False)
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


def idx_years_domains(reader, path2domains, years_and_domains, max=sys.maxint):
    ipc_codes = IPCcodes()
    path2dates = reader(max)
    c = 0
    out = open(years_and_domains, 'w')
    print "Reading", path2domains
    for line in open(path2domains):
        c += 1
        if c > max: break
        if c % 100000 == 0: print '  ', c
        path, classnames = line.rstrip("\n\r\f").split("\t")
        domains = {}
        for classname in classnames.split():
            name, domain = ipc_codes.get_domain(classname)
            if domain is not None:
                domains[domain] = True
        domains = domains.keys()
        # just take the first of the domains, not quite right but at least the
        # same as we did with WoS
        domain = None if not domains else domains[0]
        try:
            year = path2dates[path][0][:4]
        except KeyError:
            year = '9999'
        out.write("%s\t%s\t%s\n" % (path, year, domain))


def create_file_lists():
    domains = ('A41','A42','A43','A44','A45','A46','A47','A48','A49','A50')
    years = range(1995, 2015)
    fhs = {}
    for domain in domains:
        for year in years:
            fhid = "%s-%s" % (domain, year)
            fhs[fhid] = open("lists/domains/files-%s.txt" % fhid, 'w')
    c = 0
    #print fhs.keys()
    for line in open(YEARS_AND_DOMAINS_ALL):
        c += 1
        #if c > 10: break
        if c % 100000 == 0: print c
        longpath, year, domain = line.rstrip("\n\r\f").split("\t")
        #print domain, year
        if domain != 'None' and int(year) in years:
            shortpath = longpath.split('ln_cn/')[1]
            fhid = "%s-%s" % (domain, year)
            fh = fhs[fhid]
            fh.write("%s\t%s\t%s\n" % (year, longpath, shortpath))
            #print line,
    
class Index(object):

    """Not used anymore, perhaps delete it."""
    
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

    # Perform some analytics
    #
    # analyze_short_ids()
    # analyze_domains()
    # analyze_id_mapping()

    # Here is how you make the path-year-domain lists
    #
    # idx_years_domains(read_DATES2PATH_2013, PATH2DOMAINS_2013, 'lncn-2013-idx-year-domain.txt')
    # idx_years_domains(read_DATES2PATH_2014, PATH2DOMAINS_2014, 'lncn-2014-idx-year-domain.txt')

    create_file_lists()
