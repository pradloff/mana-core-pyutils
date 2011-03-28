#!/usr/bin/env python

# stdlib imports
import os
import sys
import getopt
import atexit

# 3rd party imports
import ROOT
import PyCintex; PyCintex.Cintex.Enable()

# root globals to prevent ROOT garbage collector to sweep the rug....
_root_files = []
_root_trees = []

# Root has a global dtor ordering problem: the cintex trampolines
# may be deleted before open files are closed.  Workaround is to explicitly
# close open files before terminating.
#
def _close_root_files():
    for f in _root_files:
        if hasattr (f, 'Close'): f.Close()
    del _root_files[0:-1]
    return
atexit.register(_close_root_files)

def _fnmatch(fname, patterns):
    """helper function wrapping the original `fnmatch:fnmatch` function but providing
    support for a list of patterns to match against
    """
    from fnmatch import fnmatch
    if isinstance(patterns, basestring):
        patterns = [patterns]

    for pattern in patterns:
        if fnmatch(fname, pattern):
            return True
    return False

class LBRange(object):
    def __init__(self, run, lbmin, lbmax):
        self.run = run
        self.lbmin = lbmin
        self.lbmax = lbmax

def _interpret_grl(fname):
    if not os.path.exists(fname):
        raise OSError

    lbs = []
    if fname.endswith('.dat'):
        for l in open(fname):
            l = l.strip()
            run, lbmin, lbmax = map(int, l.split())
            lbs.append(LBRange(run, lbmin, lbmax))
    elif fname.endswith('.xml'):
        data = extract_data_from_xml(fname)
        for i in data:
            run, lbmin, lbmax = map(int, i)
            lbs.append(LBRange(run, lbmin, lbmax))
    else:
        raise RuntimeError("unknown file extension (%s)" % (fname,))
    return lbs

def interpret_grl(fname="GRL.dat"):
    fnames = []
    if isinstance(fname, basestring):
        fnames = [fname]
    elif isinstance(fname, (list,tuple)):
        fnames = fname[:]
    else:
        raise TypeError('fname must be a string or a sequence (got: %s)' %
                        type(fname))
    lbs = []
    for fname in fnames:
        lbs.extend(_interpret_grl(fname))
    return lbs

def pass_grl(run, lb, good_lbs):

    for ilb in good_lbs:
        if run != ilb.run:
            continue

        if ilb.lbmin <= lb <= ilb.lbmax:
            return True

    return False

def warm_up(fname):
    assert os.path.exists(fname)
    import commands
    rc,_ = commands.getstatusoutput("/bin/dd if=%s of=/dev/null" % (fname,))
    return rc

def merge_all_trees(trees, memory, sfo, vars_fname=None, grl_fname=None):
    
    oname = sfo + ".root"
    fout = ROOT.TFile.Open(oname, "RECREATE", "", 1)

    memory *= 1024 # change to bytes


    ## summing up branch sizes over all the files
    orig_tree = trees[0]
    br_names = []
    all_br_names = [br.GetName() for br in orig_tree.GetListOfBranches()]
    if vars_fname is not None:
        # open the file containing the list of branches to keep
        br_file = open(vars_fname, 'r')
        orig_tree.SetBranchStatus("*", 0)
        print "::: keeping only the following branches: (from file-list %s)" %\
              vars_fname
        for br_name in br_file:
            br_name = br_name.strip()
            if hasattr(orig_tree, br_name) or '*' == br_name:
                print "::: [%s]" % (br_name,)
                orig_tree.SetBranchStatus(br_name, 1)
                br_names.append(br_name)
            elif '*' in br_name:
                for _i_br_name in all_br_names:
                    if _fnmatch(_i_br_name, br_name):
                        print "::: [%s] (from pattern [%s])" % (_i_br_name, br_name)
                        orig_tree.SetBranchStatus(_i_br_name, 1)
                        if not (_i_br_name in br_names):
                            br_names.append(_i_br_name)
                pass
            else:
                print "::: no such branch [%s] in tree [%s]" % (
                    br_name, orig_tree.GetName()
                    )
        br_file.close()
        del br_file
    else:
        br_names = [br.GetName() for br in orig_tree.GetListOfBranches()]

    nleaves = len(br_names)
    print "::: nleaves=[%04i] tree=[%s]" % (nleaves, orig_tree.GetName())

    tot_sz = [0]*nleaves    # zipped sizes collected from all files
    basket_sz = [0]*nleaves # size to be optimized (starts with `tot_sz`)
    baskets = [1]*nleaves   # cache

    for tree in trees:
        for ibr,br_name in enumerate(br_names):
            branch = tree.GetBranch(br_name)
            if not branch:
                print "***warning*** - tree [%s] has no branch [%s]" % (tree.GetName(),
                                                                        br_name)
                continue
            branch.SetAddress(0)

            tot_sz[ibr] += branch.GetTotBytes()
            basket_sz[ibr] = tot_sz[ibr]
            #baskets[ibr] = 1

            pass # loop over branches
        pass # loop over trees

    while 1: # recursive optimization
        tot_mem = sum(basket_sz)
        if tot_mem < memory:
            break

        max_spare = -1
        max_spare_idx = None
        for i in xrange(nleaves):
            spare = tot_sz[i]/baskets[i] - tot_sz[i]/(baskets[i]+1)
            if max_spare < spare:
                max_spare = spare
                max_spare_idx = i
        if max_spare_idx is not None:
            idx = max_spare_idx
            baskets[idx] += 1
            basket_sz[idx] = tot_sz[idx]/baskets[idx]
        pass # end-while

    # create the new (optimized) tree
    new_tree = orig_tree.CloneTree(0) # no copy of events
    # once cloning is done, separate the trees to avoid as many side-effects
    # as possible
    #orig_tree.GetListOfClones().Remove(new_tree)
    orig_tree.ResetBranchAddresses()
    new_tree.ResetBranchAddresses()

    if vars_fname is not None:
        orig_tree.SetBranchStatus("*", 0)
        new_tree.SetBranchStatus("*", 0)
        for br_name in br_names:
            orig_tree.SetBranchStatus(br_name, 1)
            new_tree.SetBranchStatus(br_name, 1)

    # setting optimized basket sizes
    tot_mem = 0.
    tot_bkt = 0
    max_bkt = 0
    min_bkt = 1024**3

    for ibr in xrange(nleaves):
        br = new_tree.GetBranch(br_names[ibr])
        if basket_sz[ibr] == 0:
            basket_sz[ibr] = 16

        basket_sz[ibr] = basket_sz[ibr] - (basket_sz[ibr] % 8)
        br.SetBasketSize(basket_sz[ibr])

        tot_mem += basket_sz[ibr]
        tot_bkt += baskets[ibr]

        if basket_sz[ibr] < min_bkt:
            min_bkt = basket_sz[ibr]
        if basket_sz[ibr] > max_bkt:
            max_bkt = basket_sz[ibr]
            
        pass # loop over leaves

    print "::: optimize baskets: "
    print "::   total memory buffer: %8.3f kb" % (tot_mem/1024,)
    print "::   total baskets:       %8.3f (min= %8.3f) (max= %8.3f) kb" % (
        tot_bkt, min_bkt, max_bkt)

    del tot_sz, basket_sz, baskets

    # copying data
    n_pass = 0
    n_tot = 0
    do_grl_selection = not (grl_fname is None)
    
    if do_grl_selection:
        good_lbs = interpret_grl(fname=grl_fname)

    print "::: processing [%i] trees..." % (len(trees,))
    for tree in trees:
        new_tree.CopyAddresses(tree)
        nentries = tree.GetEntries()
        print "::   entries:", nentries
        for i in xrange(nentries):

            nb = tree.GetEntry(i)
            if nb <= 0:
                print "*** error loading entry [%i]. got (%i) bytes" % (i,nb)
                raise RuntimeError
            n_tot += 1
            
            ## if tree.el_n < 1:
            ##     continue

            ## if tree.el_pt[0] < 10000:
            ##     continue

            ## if tree.jetmettrigbits_L1_J5 != False:
            ##     continue

            if do_grl_selection:
                if not pass_grl(tree.RunNumber, tree.lbn, good_lbs):
                    continue
                pass
            
            n_pass += 1
            new_tree.Fill()
            pass # loop over entries

        pass # loop over input trees
    print "::: processing [%i] trees... [done]" % (len(trees,))

    eff = 0
    if n_tot != 0:
        eff = n_pass/n_tot
    print "::: filter efficiency: %d/%d -> %s" % (n_pass, n_tot, eff)

    st = new_tree.Write("", ROOT.TObject.kOverwrite)
    if not st:
        print "*** File is not optimized! Not enough disk space ?"
        raise RuntimeError

    
    fout = new_tree.GetCurrentFile()
    fout.Write()
    fout.Close()

    return

def order(m, chain_name, fnames, workdir):
    chain = ROOT.TChain(chain_name)
    for fname in fnames:
        chain.Add(fname)

    files = chain.GetListOfFiles()
    nentries = files.GetEntries()
    print "::: nbr of objects:", nentries
    for i in xrange(nentries):
        elem = files.At(i)
        fn = elem.GetTitle()

        timer = ROOT.TStopwatch()
        timer.Start()
        print "::: optimizing   [%s]..." % (fn,)
        #warm_up(fn)

        timer.Start()
        fin = ROOT.TFile.Open(fn, "read")
        tmp_fname = "%s_temporary_%03i.root" % (
            chain_name.replace("/","_").replace(" ","_"),
            i)
        fout = ROOT.TFile.Open(tmp_fname, "recreate", "", 6)

        # perform the (re)ordering
        tc2 = fin.Get(chain_name)
        if m == 2:
            opt_tree = tc2.CloneTree(-1, "SortBasketsByEntry fast")
        else:
            opt_tree = tc2.CloneTree(-1, "SortBasketsByBranch fast")
        opt_tree.Write("", ROOT.TObject.kOverwrite)
        # -

        timer.Stop()

        print ":::   wallclock time:", timer.RealTime()
        print ":::   CPU time:      ", timer.CpuTime()

        fout.Close()
        fin.Close()

        dst = os.path.join(workdir, os.path.basename(fn))
        print "::: optimized as [%s]... [done]" % (dst,)
        
        # rename the temporary into the original
        import shutil
        shutil.move(src=tmp_fname,
                    dst=dst)
                                                    
        #os.rename(tmp_fname, fn)
    return

class Options(object):
    """place holder for command line options values"""
    pass

def main():

    global _root_files, _root_trees
    
    _opts = []
    _useropts = "i:o:t:m:h"
    _userlongopts = [
        "in=", "out=", "tree=", "var=", "maxsize=", "grl=", "help"
        ]
    _error_msg = """\
Accepted command line options:
 -i, --in=<INFNAME>                   ...  file containing the list of input files
 -o, --out=<OUTFNAME>                 ...  output file name
 -t, --tree=<TREENAME>                ...  name of the tree to be filtered.
                                           other trees won't be copied.
     --var=<VARSFNAME>                ...  path to file listing the branch names
                                           to be kept in the output file.
     --grl=<GRLFNAME>                 ...  path to a GRL XML file or a list of
                                           comma-separated GRL XML files
 -m, --maxsize=<sz>                   ...  maximum zip size of the main tree (in Mb.)
 """

    for arg in sys.argv[1:]:
        _opts.append(arg)
    
        opts = Options()
        opts.maxsize = 1800
        opts.vars_fname = None
        opts.grl_fname = None
        try:
            optlist, args = getopt.getopt(_opts, _useropts, _userlongopts)
        except getopt.error:
            print sys.exc_value
            print _error_msg
            sys.exit(1)

    for opt,arg in optlist:
        if opt in ("-i", "--in"):
            opts.input_files = arg

        elif opt in ("-o", "--out"):
            opts.output_file = arg

        elif opt in ("-t", "--tree"):
            opts.tree_name = str(arg).strip()

        elif opt in ("--var",):
            opts.vars_fname = arg

        elif opt in ("-m", "--maxsize"):
            opts.maxsize = int(arg)

        elif opt in ('--grl',):
            opts.grl_fname = arg

        elif opt in ("-h", "--help"):
            print _error_msg
            sys.exit(0)

    print ":"*80
    print "::: filter'n'merge d3pds"
    print ":::"
    ROOT.TTree.SetMaxTreeSize(opts.maxsize * 1024 * 1024)

    workdir = os.path.dirname(opts.output_file)
    if not os.path.exists(workdir):
        os.makedirs(workdir)

    if isinstance(opts.grl_fname, basestring):
        opts.grl_fname = opts.grl_fname.split(',')
        from glob import glob
        grl_fnames = []
        for grl_fname in opts.grl_fname:
            grl_fnames.extend(glob(grl_fname))
        opts.grl_fname = grl_fnames
        
    print "::: input files:",opts.input_files
    print "::: output file:",opts.output_file
    print "::: vars fname: ",opts.vars_fname
    print "::: tree name:  ",opts.tree_name
    print "::: GRL file:   ",opts.grl_fname
    print "::: max tree sz:",opts.maxsize

    iflist = open(opts.input_files, "r")
    for l in iflist:
        fname = l.strip()
        if not fname:
            continue
        f = ROOT.TFile.Open(fname,"read")
        if not f:
            raise RuntimeError("no such file [%s]" % fname)
        f.ResetBit(ROOT.kCanDelete)
        _root_files.append(f)
        print " - loaded [%s]" % (fname,)
        tree = f.Get(opts.tree_name)
        if not tree:
            print "***warning*** no such tree [%s] in file [%s] (IGNORING!)" % (
                opts.tree_name, fname,
                )
            continue
            ## raise RuntimeError(
            ##     "no such tree [%s] in file [%s]" %(opts.tree_name, fname)
            ##     )
        tree.ResetBit(ROOT.kCanDelete)
        _root_trees.append(tree)

    ## chain = ROOT.TChain(opts.tree_name)
    ## _root_chains.append(chain)
    
    nfiles = len(_root_files)
    if nfiles <= 0:
        print "::: no input files found"
        return 2

    timer = ROOT.TStopwatch()
    timer.Start()
    merge_all_trees(trees=_root_trees,
                    memory=1024*30,
                    sfo=opts.output_file,
                    vars_fname=opts.vars_fname,
                    grl_fname=opts.grl_fname)

    timer.Stop()

    print "::: merging done in:"
    print ":::   wallclock:",timer.RealTime()
    print ":::   CPU time: ",timer.CpuTime()

    # del _root_chains[:]
    
    print "::: performing re-ordering..."
    import glob
    fnames = glob.glob(opts.output_file+"*.root")
    order(m=2,
          chain_name=opts.tree_name,
          fnames=fnames,
          workdir=workdir)
    print "::: performing re-ordering... [done]"

    print "::: bye."
    print ":"*80
    return 0

###################### xmldict #########################
# @file PyUtils/python/xmldict.py
# @purpose converts an XML file into a python dict, back and forth
# @author http://code.activestate.com/recipes/573463
#         slightly adapted to follow PEP8 conventions

__version__ = "$Revision$"
__doc__ = """\
functions to convert an XML file into a python dict, back and forth
"""
__author__ = "Sebastien Binet <binet@cern.ch>"


# hack: LCGCMT had the py-2.5 xml.etree module hidden by mistake.
#       this is to import it, by hook or by crook
def import_etree():
    import xml
    # first try the usual way
    try:
        import xml.etree
        return xml.etree
    except ImportError:
        pass
    # do it by hook or by crook...
    import sys, os, imp
    xml_site_package = os.path.join(os.path.dirname(os.__file__), 'xml')
    m = imp.find_module('etree', [xml_site_package])

    etree = imp.load_module('xml.etree', *m)
    setattr(xml, 'etree', etree)
    return etree
try:
    etree = import_etree()
    from xml.etree import ElementTree

    ## module implementation ---------------------------------------------------
    class XmlDictObject(dict):
        def __init__(self, initdict=None):
            if initdict is None:
                initdict = {}
            dict.__init__(self, initdict)

        def __getattr__(self, item):
            return self.__getitem__(item)

        def __setattr__(self, item, value):
            self.__setitem__(item, value)

        def __str__(self):
            if '_text' in self:
                return self['_text']
            else:
                return dict.__str__(self)

        @staticmethod
        def wrap(x):
            if isinstance(x, dict):
                return XmlDictObject ((k, XmlDictObject.wrap(v))
                                      for (k, v) in x.iteritems())
            elif isinstance(x, list):
                return [XmlDictObject.wrap(v) for v in x]
            else:
                return x

        @staticmethod
        def _unwrap(x):
            if isinstance(x, dict):
                return dict ((k, XmlDictObject._unwrap(v))
                             for (k, v) in x.iteritems())
            elif isinstance(x, list):
                return [XmlDictObject._unwrap(v) for v in x]
            else:
                return x

        def unwrap(self):
            return XmlDictObject._unwrap(self)

        pass # Class XmlDictObject
    
    def _dict2xml_recurse(parent, dictitem):
        assert type(dictitem) is not type(list)

        if isinstance(dictitem, dict):
            for (tag, child) in dictitem.iteritems():
                if str(tag) == '_text':
                    parent.text = str(child)
                elif type(child) is type(list):
                    for listchild in child:
                        elem = ElementTree.Element(tag)
                        parent.append(elem)
                        _dict2xml_recurse (elem, listchild)
                else:                
                    elem = ElementTree.Element(tag)
                    parent.append(elem)
                    _dict2xml_recurse (elem, child)
        else:
            parent.text = str(dictitem)
    
    def dict2xml(xmldict):
        """convert a python dictionary into an XML tree"""
        roottag = xmldict.keys()[0]
        root = ElementTree.Element(roottag)
        _dict2xml_recurse (root, xmldict[roottag])
        return root

    def _xml2dict_recurse (node, dictclass):
        nodedict = dictclass()

        if len(node.items()) > 0:
            # if we have attributes, set them
            nodedict.update(dict(node.items()))

        for child in node:
            # recursively add the element's children
            newitem = _xml2dict_recurse (child, dictclass)
            if nodedict.has_key(child.tag):
                # found duplicate tag, force a list
                if type(nodedict[child.tag]) is type([]):
                    # append to existing list
                    nodedict[child.tag].append(newitem)
                else:
                    # convert to list
                    nodedict[child.tag] = [nodedict[child.tag], newitem]
            else:
                # only one, directly set the dictionary
                nodedict[child.tag] = newitem

        if node.text is None: 
            text = ''
        else: 
            text = node.text.strip()

        if len(nodedict) > 0:            
            # if we have a dictionary add the text as a dictionary value
            # (if there is any)
            if len(text) > 0:
                nodedict['_text'] = text
        else:
            # if we don't have child nodes or attributes, just set the text
            if node.text: nodedict = node.text.strip()
            else:         nodedict = ""



        return nodedict
        
    def xml2dict (root, dictclass=XmlDictObject):
        """convert an xml tree into a python dictionary
        """
        return dictclass({root.tag: _xml2dict_recurse (root, dictclass)})
    #####################################################################

except ImportError:
    print "**WARNING: could not import 'xml.etree' (check your python version)"
    print "           you won't be able to correctly read GRL XML files !"
    
def extract_data_from_xml(fname="GRL.xml"):
    """simple helper function to convert a GRL xml file into a list
    of tuples (run-nbr, lumi-block-start, lumi-block-stop)
    """
    import sys
    assert "xml.etree" in sys.modules, \
           "no 'xml.etree' module were imported/available"
    data =[]
    dd=xml2dict(etree.ElementTree.parse(str(fname)).getroot())

    lbks = dd['LumiRangeCollection']['NamedLumiRange']['LumiBlockCollection']
    if not isinstance(lbks, (list, tuple)):
        lbks = [lbks]
    for lbk in lbks:
        assert isinstance(lbk,dict), \
               "expect a dict-like object (got type=%s - value=%r)" % (type(lbk), repr(lbk))
        runnumber=lbk['Run']
        run_ranges=lbk['LBRange']

        #xml2dict return a dataset when only one lbn range per run
        #and return a list when there are several lbn ranges per run
        #==> need different piece of code
        #The following lines 'convert' a dict into a list of 1 dict 
        if isinstance(run_ranges,dict):
            run_ranges=[run_ranges]
            pass

        #loop over run ranges
        for lbrange in run_ranges: 
            lbn_min=lbrange['Start']
            lbn_max=lbrange['End']
            #print runnumber,"  ", lbn_min,"  ", lbn_max
            data.append((runnumber, lbn_min, lbn_max))
            pass
    return data

### script entry point ###
if __name__ == "__main__":
    sys.exit(main())
