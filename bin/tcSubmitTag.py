#!/usr/bin/env python

__version__ = "$Revision$"
__doc__ = """\
 Submit one or more TAGs to TagCollector. TAG can be in one of two formats:
    Container/Package-00-01-02
    Package-00-01-02
 All submitted tags need approval via the TagCollector web interface.
 If several TAGs are given they will be submitted to the same release(s)
 with the same justification, etc. Optionally a bundle name can be specified.
 If no release number is given a list of available releases is presented.

 For any required argument that is not specified on the command line,
 an interactive query is presented. Some text fields support history (arrow keys).

 To authenticate via your grid certificate, set:
    export X509_USER_PROXY=~/private/x509proxy 
 and execute in a separate shell(!) (or via bash -c)
    source /afs/cern.ch/project/gd/LCG-share/current/etc/profile.d/grid_env.sh
    voms-proxy-init -voms atlas -out X509_USER_PROXY'
 Once created the voms proxy is usable from any machine that has access to it.
 """
__author__ = "Frank Winklmeier"

import sys
import os

# Hack for 15.4.0 to get xml.etree back
#sys.path.insert(0,"/afs/cern.ch/sw/lcg/external/Python/2.5.4/slc4_ia32_gcc34/lib/python2.5")

# Hack since AMI environment is incompatible with athena
#sys.path.append("/afs/cern.ch/atlas/offline/external/ZSI/1.7.0/lib/python")
#sys.path.append("/afs/cern.ch/sw/lcg/external/4suite/1.0.2_python2.5/slc4_ia32_gcc34/lib/python2.5/site-packages")

import string
import getpass
import readline
from pyAMI.pyAMI import *
amiclient = AMI(certAuth = True)
   
def tcExecCmd(cmd, args, debug=False):
   """Execute a TC command"""

   # Add some default arguments
   args['project'] = 'TagCollector'
   args['processingStep'] = 'production'
   args['repositoryName'] = 'AtlasOfflineRepository'

   # Transform into AMI command string
   amiCmd = map(lambda a,b:a+"="+b,args.keys(),args.values())
   amiCmd.insert(0, cmd)

   if debug:
      print amiCmd
      return True

   # Execute
   try:
      result = amiclient.execute(amiCmd)
      return result
   except Exception, msg:
      print msg
      return None

   
def submitTag(opt, pkg, tag):
   """Submit tag"""

   arg = {}
   arg['action'] = 'update'
   arg['fullPackageName'] = pkg
   arg['packageTag'] = tag
   arg['autoDetectChanges'] = 'yes'

   if opt.user and opt.password:
      arg['AMIUser'] = opt.user
      arg['AMIPass'] = opt.password

   if opt.justification: arg['justification'] = opt.justification
   if opt.savannah: arg['bugReport'] = opt.savannah
   if opt.bundle: arg['bundleName'] = opt.bundle
   if opt.noMail: arg['noMail'] = ''
   
   for i,p in enumerate(opt.project):
     arg['groupName'] = p
     arg['releaseName'] = opt.release[i]
     ok = tcExecCmd('TCSubmitTagApproval', arg, debug=False)
     if ok:
         print "%s %s submitted to %s %s" % (pkg,tag,p,opt.release[i])


def findPkg(pkg):
  """Find the full path name of a package. Return (pkg,tag) tuple."""

  # If "-" in name, tag was given
  if pkg.find('-')!=-1:
     tag = pkg.split('/')[-1]
     pkg = pkg.split('-',1)[0]
  else:
     raise RuntimeError("No tag was given for %s" % pkg)
   
  # If no "/" in name, need to find full package path
  if pkg.find('/')!=-1:
     return (pkg,tag)
  
  arg = {}
  arg['glite'] = ("select packages.path,packages.packageName "
                  "where repositories.repositoryName='AtlasOfflineRepository' "
                  "and packages.packageName='%s'" % pkg)

  result = tcExecCmd('SearchQuery', arg)
  if not result:
     raise RuntimeError("Could not resolve %s to full package path" % pkg)
  
  pkgList = []
  for v in result.getDict()['Element_Info'].values():
    pkgList += [v['path']+v['packageName']]
  
  if len(pkgList)==0:
    raise RuntimeError("Package '%s' does not exist" % pkg)

  elif len(pkgList)>1:
    print "Multiple packages found for %s:" % pkg
    for i,v in enumerate(pkgList):
        print "%i) %s" % (i+1,v)
    n = int(raw_input("Please select: "))
    pkg = pkgList[n-1]

  else:
    pkg = pkgList[0]

  # Make sure package path starts with slash
  if pkg[0]!='/':
      pkg = '/'+pkg
   
  return (pkg,tag)

   
def queryOpt(option):
   """Query option from user and set proper history files"""
   
   fHistory = None
   if option.dest in ["project","release","justification"]:
      fHistory = os.path.expanduser('~/.tc_submit_tag.%s.history' % option.dest)
      if os.path.exists( fHistory ):
         readline.read_history_file( fHistory )
         
   value = raw_input(option.prompt+": ")

   if fHistory: readline.write_history_file( fHistory )
   readline.clear_history()

   if value=='': return None
   else:         return value
   


def queryRelease(releases, project):
   """Query the release(s) to submit to"""

   if len(releases)==1: return releases[0]

   print "Available releases for %s:" % project
   for r in releases:
       print "  %s" % r

   readline.clear_history()
   for r in reversed(releases):
       readline.add_history(r)
      
   choice = raw_input("Select (comma separated or '*' for all): ")

   if choice=='*': return ','.join(releases)
   else:           return choice
   
      
def getOpenReleases(project):
   """Return list of open releases for given project"""
   
   arg = {}
   arg['groupName'] = project
   arg['expandedRelease'] = '*'   
   result = tcExecCmd('TCFormGetReleaseTreeDevView', arg)
   if not result:
      raise RuntimeError(
          "Could not find open releases in project %s" % project
          )
  
   rxml = result.transform('xml')
   import xml.etree.cElementTree as ET
   
   # Definition of available releases depends on project
   #if project in ["AtlasP1HLT","AtlasTier0"]:
   #   cond = lambda x: x.get("status")!="terminated"
   #else:
   #   cond = lambda x: x.get("status")!="terminated" and x.get("tagApprovalMode")=="tagApproval"

   cond = lambda x: x.get("status")!="terminated"
   try:
      reltree = ET.fromstring(
          result.transform("xml")
          ).find("Result").find("tree")
      releases = [ r.get("releaseName") 
                   for r in reltree.getiterator("treeBranch") 
                   if cond(r) ]
      
      # Filter all special purpose releases (e.g. -MIG, -SLHC)
      releases = filter(lambda x: x.count("-")==0, releases)
   except Exception, e:
      print e.message
      raise RuntimeError(
          'Could not parse result of TCFormGetReleaseTreeDevView:\n%s' % rxml
          )

   return releases


def myhelp(option, opt_str, value, parser):
   """Custom help callback since optparse does not preserve newlines"""

   print " Usage: tcSubmitTag.py [OPTIONS] TAG ..."
   print
   print __doc__
   
   parser.print_help()
   sys.exit(1)


def validCertificate():
   return (
       os.environ.has_key("X509_USER_PROXY") and
       os.path.exists(os.environ['X509_USER_PROXY'])
       )


def main():
   
   import optparse
   parser = optparse.OptionParser(usage = "",
                                  add_help_option = False)
   add = parser.add_option
   
   add("-p", dest="project", action="store",
       help="Project(s) (comma separated list)").prompt = "Project(s)"
   
   add("-r", dest="release", action="store",
       help="Release(s) (comma separated list)").prompt = "Release(s)"
   
   add("-j", dest="justification", action="store",
       help="Justification for tag request").prompt = "Justification"
   
   add("-s", dest="savannah", action="store", metavar="BUG",
       help="Savannah bug report number").prompt = "Savannah bug report"
   
   add("-u", dest="user", action="store",
       help="AMI user name (if $AMIUser not set and no voms-proxy)")

   add("-b", dest="bundle", action="store",
       help="Bundle name (stays incomplete)")

   add("-n", "--noMail", action="store_true",
       help="Do not send confirmation email")

   add("-h", "--help", action="callback", callback=myhelp)

   
   (opt, args) = parser.parse_args()   

   if len(args)==0:
      myhelp(None,None,None,parser)
      return 1

   # Create a list of (pkg,tag) with full package path
   pkgList = [findPkg(p) for p in args]
      
   # Setup history
   readline.set_history_length(10)

   if opt.project and not opt.release:
      for p in opt.project.split(','):
         rel = getOpenReleases(p)
         if len(rel)==0: continue
         if not opt.release: 
            opt.release = queryRelease(rel,p)
         else:
            opt.release += (",%s" % queryRelease(rel,p))
   
   # Query for missing options   
   print '-'*80
   for o in parser.option_list:
      # Only for options that have this addition attribute
      if not hasattr(o,"prompt"): continue      
      value = getattr(opt, o.dest)
      if value:
         print o.prompt + ": " + value
      else:
         setattr(opt, o.dest, queryOpt(o))         
   print '-'*80
   
   opt.project = opt.project.split(',')
   opt.release = opt.release.split(',')
   if len(opt.project)!=len(opt.release):
      raise RuntimeError(
          'Number of projects %s and releases %s do not match' %
          (opt.project, opt.release)
          )

   ok = False
   if validCertificate():
      opt.password = None
      choice = raw_input("Submit tag? [Y/n] ")      
      ok = len(choice)==0 or choice.upper()=="Y"
   else:
      # Get user name via env var or prompt
      if not opt.user: opt.user = os.environ.get("AMIUser",None)      
      if not opt.user: opt.user = raw_input("AMI user name: ")
      
      opt.password = getpass.getpass("Enter AMI password to submit: ")
      ok = len(opt.password)>0

   if ok:
      # Submit tag request
      for p in pkgList: submitTag(opt,p[0],p[1])
   else:
      print "Tag submission aborted"
         

if __name__ == "__main__":
   try:
      sys.exit(main())
   except RuntimeError, e:
      print "ERROR:",e.message
      sys.exit(1)
   except KeyboardInterrupt:
      sys.exit(1)
      
