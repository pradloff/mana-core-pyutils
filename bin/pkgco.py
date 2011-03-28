#!/usr/bin/env python
#
# @file:    pkgco.py
# @purpose: Checkout a given package. Find container names and release tag
#           if not explicitly given (inspired by BaBar's 'addpkg' command).
# @author:  Frank Winklmeier
#
# $Id: pkgco,v 1.4 2009/03/25 14:25:46 fwinkl Exp $

__version__ = "$Revision: 1.4 $"

import sys
import os
import getopt
import string
from PyCmt import Cmt

try:
   import multiprocessing as mp
except ImportError:
   mp = None

def usage():
   print """\
Usage: pkgco.py [OPTION]... PACKAGE...

Checkout PACKAGE from the release. Possible formats:
  Package                  find container and checkout tag in release
  Package-X-Y-Z            find container and checkout specified tag
  Container/Package        checkout tag in release
  Container/Package-X-Y-Z  checkout specified tag

where OPTION is:
  -A    checkout the HEAD/trunk of the package(s)
  -f    FILE contains PACKAGE list (one per line)
  -s    only show package version, no checkout
"""
   return


def findPkg(pkg):
  """Find package version in release."""

  cmt = Cmt.CmtWrapper()
  cmtPkg = cmt.find_pkg(name=pkg)
  
  if cmtPkg:
    return os.path.join(cmtPkg.path,cmtPkg.name)
  else:
    raise RuntimeError, "Package '%s' does not exist" % pkg         


def checkout(pkg, head, doCheckOut = True):
   """Checkout one package."""

   tag = ""
   # If "-" in name, tag was given
   if pkg.find('-') != -1:
      tag = pkg.split('/')[-1]   # remove container packages
      pkg = pkg.split('-',1)[0]  # package name
      
   # If no "/" in name, need to find full package path
   if pkg.find('/')==-1: pkg = findPkg(pkg)      

   # Remove leading "/" for CMT checkout
   pkg = string.lstrip(pkg, "/")
   
   if head:
     os.system("cmt co %s" % pkg)
     return
   
   if len(tag)==0:
      versions = os.popen("cmt show versions %s" % pkg).readlines()
      versions = [v for v in versions if v.find(os.environ["TestArea"])==-1]
      if len(versions)>1:
         print "Found the following versions:"
         for v in versions: print v

      if len(versions)>0:
         tag = versions[0].split(" ")[1]

   if len(tag)==0:
      raise RuntimeError, "Could not find any tag for '%s'" % pkg

   if doCheckOut:
      os.system("cmt co -r %s %s" % (tag,pkg))
   else:
      print tag,pkg
      
   return
   
def safe_checkout(args):
   try:
      checkout(*args)
   except RuntimeError, e:
      print e
      
def main():

   try:
      opts,args = getopt.gnu_getopt(sys.argv[1:], "hAsf:v", ["help","version"])
   except getopt.GetoptError, e:
      print e
      usage()
      return 1

   # Parse command line
   head = False
   pkgFile = None
   doCheckOut = True
   for o,a in opts:
      if o == "-A":
         head = True
      elif o == "-f":
         pkgFile = a
      elif o == "-s":
         doCheckOut = False
      elif o in ("-h", "--help"):
         usage()
         return 0
      elif o in ("-v", "--version"):
         print __version__.strip("$")
         return 0
      
   if (pkgFile is None) and (len(args)==0):
      usage()
      return 1

   # Read optional file with package tags
   pkgList = args
   if pkgFile:
      try:
         f = open(pkgFile)
      except IOError:
         print "Cannot open file '%s'." % pkgFile
         return 2
         
      for line in f: pkgList.append(line.strip())

   # Checkout packages
   args = zip(pkgList,
              [head]*len(pkgList),
              [doCheckOut]*len(pkgList))

   # allow to process multiple packages in parallel
   if mp and len(pkgList)>1:
      print "enabling parallel checkout..."
      pool = mp.Pool()
      res = pool.map_async(safe_checkout, args)
      res.get()
   else:
      map(safe_checkout, args)

   return 0

if __name__ == "__main__":
   try:   
      sys.exit(main())
   except RuntimeError, e:
      print e
      sys.exit(1)
   except KeyboardInterrupt:
      sys.exit(1)
      
