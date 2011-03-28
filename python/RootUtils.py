# @file PyUtils.RootUtils
# @author Sebastien Binet
# @purpose a few utils to ease the day-to-day work with ROOT
# @date November 2009

from __future__ import with_statement

__doc__ = "a few utils to ease the day-to-day work with ROOT"
__version__ = "$Revision$"
__author__ = "Sebastien Binet"

__all__ = [
    'import_root',
    'root_compile',
    ]

### imports -------------------------------------------------------------------
import os
import sys
import re
from pprint import pprint

try:
    import simplejson as json
except ImportError:
    import json

from .Decorators import memoize

### functions -----------------------------------------------------------------
def import_root(batch=True):
    """a helper method to wrap the 'import ROOT' statement to prevent ROOT
    from screwing up the display or loading graphics libraries when in batch
    mode (which is the default.)

    e.g.
    >>> ROOT = import_root(batch=True)
    >>> f = ROOT.TFile.Open(...)
    """
    import sys
    if batch:
        sys.argv.insert(1, '-b')
    import ROOT
    ROOT.gROOT.SetBatch(batch)
    if batch:
        del sys.argv[1]
    import PyCintex
    PyCintex.Cintex.Enable()
    return ROOT

def root_compile(src=None, fname=None, batch=True):
    """a helper method to compile a set of C++ statements (via ``src``) or
    a C++ file (via ``fname``) via ACLiC
    """
    if src is not None and fname is not None:
        raise ValueError("'src' xor 'fname' should be not None, *not* both")

    if src is None and fname is None:
        raise ValueError("'src' xor 'fname' should be None, *not* both")

    import os
    from .Helpers import ShutUp as root_shutup
    
    ROOT = import_root(batch=batch)
    compile_options = "f"
    if 'dbg' in os.environ.get('CMTCONFIG', 'opt'):
        compile_options += 'g'
    else:
        compile_options += 'O'

    src_file = None
    if src:
        import textwrap
        import tempfile
        src_file = tempfile.NamedTemporaryFile(prefix='root_aclic_',
                                               suffix='.cxx')
        src_file.write(textwrap.dedent(src))
        src_file.flush()
        src_file.seek(0)
        fname = src_file.name
        pass

    elif fname:
        import os.path as osp
        fname = osp.expanduser(osp.expandvars(fname))
        pass
        
    assert os.access(fname, os.R_OK), "could not read [%s]"%(fname,)
    orig_root_lvl = ROOT.gErrorIgnoreLevel
    ROOT.gErrorIgnoreLevel = ROOT.kWarning
    try:
        with root_shutup():
            sc = ROOT.gSystem.CompileMacro(fname, compile_options)
        if sc == ROOT.kFALSE:
            raise RuntimeError(
                'problem compiling ROOT macro (rc=%s)'%(sc,)
                )
    finally:
        ROOT.gErrorIgnoreLevel = orig_root_lvl
    return
        
@memoize
def _pythonize_tfile():
    import PyCintex; PyCintex.Cintex.Enable()
    root = import_root()
    PyCintex.loadDict("RootUtilsPyROOTDict")
    rootutils = getattr(root, "RootUtils")
    pybytes = getattr(rootutils, "PyBytes")
    read_root_file = getattr(rootutils, "_pythonize_read_root_file")
    tell_root_file = getattr(rootutils, "_pythonize_tell_root_file")
    def read(self, size=-1):
        """read([size]) -> read at most size bytes, returned as a string.

        If the size argument is negative or omitted, read until EOF is reached.
        Notice that when in non-blocking mode, less data than what was requested
        may be returned, even if no size parameter was given.

        FIXME: probably doesn't follow python file-like conventions...
        """
        SZ = 4096
        
        if size>=0:
            #size = _adjust_sz(size)
            #print "-->0",self.tell(),size
            c_buf = read_root_file(self, size)
            if c_buf and c_buf.sz:
                #print "-->1",self.tell(),c_buf.sz
                #self.seek(c_buf.sz+self.tell())
                #print "-->2",self.tell()
                buf = c_buf.buffer()
                buf.SetSize(c_buf.sz)
                return str(buf[:])
            return ''
        else:
            size = SZ
            out = []
            while True:
                #size = _adjust_sz(size)
                c_buf = read_root_file(self, size)
                if c_buf and c_buf.sz:
                    buf = c_buf.buffer()
                    buf.SetSize(c_buf.sz)
                    out.append(str(buf[:]))
                else:
                    break
            return ''.join(out)
    root.TFile.read = read
    del read
    
    root.TFile.seek = root.TFile.Seek
    root.TFile.tell = lambda self: tell_root_file(self)
    ## import os
    ## def tell(self):
    ##     fd = os.dup(self.GetFd())
    ##     return os.fdopen(fd).tell()
    ## root.TFile.tell = tell
    ## del tell
    return 


class RootDumper(object):
    """
    A helper class to dump in more or less human readable form the content of
    any TTree.
    """
    
    def __init__(self, fname, 
                 tree_filter=None,
                 branch_filter=None,
                 output=None,
                 reference=None):
        object.__init__(self)

        import AthenaPython.PyAthena as PyAthena
        _pyroot_inspect = PyAthena.RootUtils.PyROOTInspector.pyroot_inspect
        self._pythonize = _pyroot_inspect

        self.tree_filter = tree_filter
        self.branch_filter = branch_filter
        if output is None:
            output = os.path.basename(fname) + ".ascii"
        self.fout = open(output, "w")
        self.reference = reference

        self.root_file = PyAthena.TFile.Open(fname)
        print ":: input file [%s]" % (fname,)
        return

    def dump_trees(self):

        import AthenaPython.PyAthena as PyAthena
        tree_names = []
        keys = [k.GetName() for k in self.root_file.GetListOfKeys()]
        for k in keys:
            o = self.root_file.Get(k)
            if isinstance(o, PyAthena.TTree):
                tree_names.append(k)
        
        # filter based on self.tree_filter
        # ...

        tree_names = sorted(tree_names)
        for n in tree_names:
            self.dump_tree(n)

        return

    def dump_tree(self, tree_name):
        import AthenaPython.PyAthena as PyAthena
        tree = self.root_file.Get(tree_name)
        assert isinstance(tree, PyAthena.TTree)

        hdr = "%s tree [%s] %s" % (":"*20, tree_name, ":"*20,)
        print hdr
        print >> self.fout, hdr

        #tree.Print()

        nentries = tree.GetEntries()
        
        for i in xrange(nentries):
            hdr = ":: entry [%05i]..." % (i,)
            print hdr
            print >> self.fout, hdr

            nbytes = tree.GetEntry(i)
            if nbytes <= 0:
                print "**err** reading entry [%s] of tree [%s]" % (i, tree_name)
                hdr = ":: entry [%05i]... [ERR]" % (i,)
                print hdr
                print >> self.fout, hdr
                continue

            self.dump_branches(tree, entry=i)
            hdr = ":: entry [%05i]... [DONE]" % (i,)
            print hdr
            print >> self.fout, hdr

        hdr = "%s tree [%s] %s [DONE]" % (":"*20, tree_name, ":"*20,)
        print hdr
        print >> self.fout, hdr
        return

    def dump_branches(self, tree, entry):
        branches = sorted([b.GetName() for b in tree.GetListOfBranches()])
        nbranches = len(branches)

        _pythonize = self._pythonize

        for br_name in branches:
            hdr = "::  branch [%s]..." % (br_name,)
            print hdr
            print >> self.fout, hdr

            # load data
            nbytes = b.GetEntry(entry)
            if nbytes <= 0:
                print "**err** while reading branch [%s]" % (br_name,)
                continue
            pyobj = getattr(tree, br_name)
            if not (pyobj is None):
                #print pyobj
                #print _pythonize(pyobj)
                print >> self.fout, _pythonize(pyobj)
                #pprint(_pythonize(pyobj), stream=self.fout, width=120)
                #json.dump(_pythonize(pyobj), fp=self.fout, indent=" ")
            else:
                print "**warn** type [%s] of branch [%s] is NOT handled" % (
                    b.Class().GetName(), br_name)
            pass # loop over branch names
        return

    pass # class RootDumper

### test support --------------------------------------------------------------
def _test_main():
    root = import_root()
    def no_raise(msg, fct, *args, **kwds):
        caught = False
        try:
            fct(*args, **kwds)
        except Exception, err:
            caught = True
        assert not caught, "%s:\n%s\nERROR" % (msg, err,)

    no_raise("problem pythonizing TFile", fct=_pythonize_tfile)
    no_raise("problem compiling dummy one-liner",
             root_compile, "void foo1() { return ; }")
    no_raise("problem compiling dummy one-liner w/ kwds",
             fct=root_compile, src="void foo1() { return ; }")
    import tempfile
    with tempfile.NamedTemporaryFile(prefix="foo_",suffix=".cxx") as tmp:
        print >> tmp, "void foo2() { return ; }"
        tmp.flush()
        no_raise("problem compiling a file",
                 fct=root_compile, fname=tmp.name)

    print "OK"

if __name__ == "__main__":
    _test_main()
    
