#!/usr/bin/env python
#
# @file:    pkgco.py
# @purpose: Checkout a given package. Find container names and release tag
#           if not explicitly given (inspired by BaBar's 'addpkg' command).
# @author:  Frank Winklmeier
#
# $Id: pkgco,v 1.4 2009/03/25 14:25:46 fwinkl Exp $

__version__ = "$Revision: 1.4 $"
__author__  = "Frank Winklmeier"

import sys
import os
import getopt
import string
import subprocess
from PyCmt import Cmt

try:
   import multiprocessing as mp
except ImportError:
   mp = None

cmt = Cmt.CmtWrapper()

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
  -r    show most recent version, no checkout
"""
   return

def findPkg(pkg):
  """Find package version in release."""

  cmtPkg = cmt.find_pkg(name=pkg)
  
  if cmtPkg:
    return os.path.join(cmtPkg.path,cmtPkg.name)
  else:
    raise RuntimeError, "Package '%s' does not exist" % pkg         


def svn_tag_equals_trunk(pkg,tag):
   """Do an SVN diff of pkg/tag with trunk

   Return: True/False
   """

   svnroot = os.environ.get("SVNROOT")
   if svnroot==None:
      raise RuntimeError, "SVNROOT is not set"

   pkg = os.path.join(svnroot, pkg)
   cmd = "svn diff %s/tags/%s %s/trunk" % (pkg,tag,pkg)
   p = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell=True)
   stdout,stderr = p.communicate()
   if stderr!=None:
      print stderr
      return False
   
   return len(stdout)==0

      
def checkout(pkg, head, doCheckOut=True, showRecent=False):
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
      tag = cmt.get_pkg_version(pkg)      
      if tag==None:
         raise RuntimeError, "Could not find any tag for '%s'" % pkg

   if doCheckOut:
      os.system("cmt co -r %s %s" % (tag,pkg))
   else:
      msg = "%s %s" % (tag,pkg)
      if (showRecent):
         headversion = cmt.get_latest_pkg_tag(pkg)
         if headversion!=None:
            istrunk = svn_tag_equals_trunk(pkg,headversion)
         else:
            istrunk = False
            headversion="NONE"

         msg += "  (most recent %s %s trunk)" % (headversion, "==" if istrunk else "!=")

            
      print msg
      
   return
   
def safe_checkout(args):
   try:
      checkout(*args)
   except RuntimeError, e:
      print e
      
def main():

   try:
      opts,args = getopt.gnu_getopt(sys.argv[1:], "hAsrf:v", ["help","version"])
   except getopt.GetoptError, e:
      print e
      usage()
      return 1

   # Parse command line
   head = False
   pkgFile = None
   doCheckOut = True
   showRecent = False
   for o,a in opts:
      if o == "-A":
         head = True
      elif o == "-f":
         pkgFile = a
      elif o == "-s":
         doCheckOut = False
      elif o == "-r":
         showRecent = True
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
              [doCheckOut]*len(pkgList),
              [showRecent]*len(pkgList))

   # allow to process multiple packages in parallel
   if mp and len(pkgList)>1 and doCheckOut:
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
      
