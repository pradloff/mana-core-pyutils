# @file PyUtils.scripts.tc_submit_pkg
# @purpose Submit one or more TAGs to TagCollector.
# @author Sebastien Binet
# @date February 2010

__version__ = "$Revision$"
__doc__ = "Submit one or more TAGs to TagCollector."
__author__ = "Sebastien Binet, Frank Winklmeier"


### imports -------------------------------------------------------------------
import readline
import getpass
import os
import os.path as osp

import PyUtils.acmdlib as acmdlib
import PyUtils.AmiLib as amilib

### functions -----------------------------------------------------------------

def query_option(opt_name):
    """query option from user and set proper history files"""
    history_file = None
    _allowed_values = ('project', 'release', 'justification', 'savannah',)
    if opt_name not in _allowed_values:
        raise ValueError(
            "'opt_name' must be in %s (got %s)" %
            _allowed_values,
            opt_name
            )
    history_file = osp.expanduser('~/.tc_submit_tag.%s.history' % opt_name)
    if osp.exists(history_file):
        readline.read_history_file(history_file)

    value = raw_input('%s: ' % opt_name)
    if history_file:
        readline.write_history_file(history_file)
    readline.clear_history()

    if value == '':
        return None
    return value

def _get_projects(client, release, pkg):
    """retrieve the list of projects from AMI for a given release and package
    """
    projects = []
    full_pkg_name = pkg['packagePath']+pkg['packageName'] # pkg['packageTag']
    try:
        res = client.exec_cmd(cmd='TCGetPackageVersionHistory',
                              fullPackageName=full_pkg_name,
                              releaseName=release)
        d = amilib.ami_todict(res)['AMIMessage']['Result']
        rows = d['rowset']
        if isinstance(rows, dict):
            rows = [rows]
        ## print "---"
        ## print dict(d)
        ## print "---"
        for row in rows:
            if not row['type'] in ('Package_version_history',
                                   'Package_version_history_delete'):
                ## print "-- skip [%s]" % row['type']
                continue
            fields = row['row']['field']
            for field in fields:
                n = field.get('name', None)
                v = field.get('_text', None)
                ## print "[%s] => [%s]" % (n,v)
                if n == 'groupName':
                    ## print "-->",v
                    projects.append(v)
                    #return v
        if not projects:
            print "::: no project found for package [%s] and release [%s]" % (
                full_pkg_name,
                release)
    except amilib.PyAmi.AMI_Error, err:
        pass
    return projects
    
def query_project(projects, release, pkg):
    """query the project(s) to submit to"""
    if len(projects)==1:
        return projects[0]

    print "::: Available projects for package [%s] and release [%s]" % (
        pkg,
        release)
    for p in projects:
        print "   %s" % (p,)

    readline.clear_history()
    for r in reversed(projects):
        readline.add_history(p)

    choice = raw_input("Select (comma separated or '*' for all): ")

    if choice=='*':
        return ','.join(projects)
    return choice

def query_release(releases, project):
    """query the release(s) to submit to"""

    if len(releases)==1:
        return releases[0]

    print "::: Available releases for %s:" % (project,)
    for r in releases:
        print "  %s" % (r,)

    readline.clear_history()
    for r in reversed(releases):
        readline.add_history(r)

    choice = raw_input("Select (comma separated or '*' for all): ")

    if choice=='*':
        return ','.join(releases)
    return choice
   
def valid_certificate():
    return (
        'X509_USER_PROXY' in os.environ and
        osp.exists(os.environ['X509_USER_PROXY'])
        )

def submit_tag(client, args, pkg, tag):
   """Submit tag"""

   cmd_args = {}
   cmd_args['action'] = 'update'
   cmd_args['fullPackageName'] = pkg
   cmd_args['packageTag'] = tag
   cmd_args['autoDetectChanges'] = 'yes'

   if args.user and args.password:
      cmd_args['AMIUser'] = args.user
      cmd_args['AMIPass'] = args.password

   if args.justification: cmd_args['justification'] = args.justification
   if args.savannah: cmd_args['bugReport'] = args.savannah
   if args.bundle: cmd_args['bundleName'] = args.bundle
   if args.no_mail: cmd_args['noMail'] = ''
   
   for i,p in enumerate(args.project):
     cmd_args['groupName'] = p
     cmd_args['releaseName'] = args.release[i]
     ok = client.exec_cmd(cmd='TCSubmitTagApproval', args=cmd_args)
     if ok:
         print "%s %s submitted to %s %s" % (pkg,tag,p,args.release[i])

@acmdlib.command(name='tc.submit-tag')
@acmdlib.argument(
    '-p', '--project',
    action='store',
    help='(comma separated list of) project(s) to submit tags to')
@acmdlib.argument(
    '-r', '--release',
    action='store',
    help='(comma separated list of) release(s) to submit tags to')
@acmdlib.argument(
    '-j', '-m', '--justification',
    action='store',
    help='justification for tag request')
@acmdlib.argument(
    '-s', '--savannah',
    action='store',
    metavar='BUG',
    help='savannah bug report number')
@acmdlib.argument(
    '-u', '--user',
    action='store',
    help="AMI user name (if $AMIUser not set and no voms-proxy)")
@acmdlib.argument(
    '-b','--bundle',
    action='store',
    help="Bundle name (stays incomplete)")
@acmdlib.argument(
    '-n', '--no-mail',
    action='store_true',
    default=False,
    help="Do not send confirmation email")
@acmdlib.argument(
    '--password',
    default='',
    help='password for AMI. do not use in clear text !'
    )
@acmdlib.argument(
    '--dry-run',
    action='store_true',
    default=False,
    help='switch to simulate the commands but not actually send the requests'
    )
@acmdlib.argument(
    'pkgs',
    nargs='+',
    help="""\
    (list of package) tags to submit or a file containing that list""")
def main(args):
    """Submit one or more TAGs to TagCollector.


    TAG can be in one of two formats:
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

    import PyUtils.AmiLib as amilib
    client = amilib.Client()


    def select_tag():
        value = raw_input('Please select (q to quit): ')
        if value.lower() == 'q':
            raise StopIteration
        return int(value)
    
    # create a list of (pkg,tag) with full package path
    pkgs = []

    for pkg in args.pkgs:
        # a file ?
        if osp.exists(pkg):
            fname = pkg
            print "::: taking tags from file [%s]..." % (fname,)
            for l in open(fname, 'r'):
                l = l.strip()
                if l:
                    print " - [%s]" % (l,)
                    pkgs.append(l)
        else:
            pkgs.append(pkg)
    pkgs = list(set(pkgs))
    pkg_list = [client.find_pkg(pkg, cbk_fct=select_tag) for pkg in pkgs]

    # setup history
    readline.set_history_length(10)

    # query release if project is known
    if args.project and not args.release:
        for p in args.project.split(','):
            rel = client.get_open_releases(p)
            if len(rel)==0:
                continue
            if not args.release:
                args.release = query_release(rel, p)
            else:
                args.release += (',%s' % query_release(rel, p))
    if args.release and len(args.release.split(',')) == 1:
        _release = args.release.split(',')[0]
        args.release = ','.join([_release]*len(pkg_list))
        # adjust the project list too
        if args.project and len(args.project.split(',')) == 1:
            args.project = ','.join([args.project.split(',')[0]]*len(pkg_list))
            
    # query project if release is known
    if args.release and not args.project:
        _releases = args.release.split(',')
        _projects = []
        rel = _releases[0]
        for pkg in pkg_list:
            proj = _get_projects(client, rel, pkg)
            if len(proj)==0:
                _projects.append(None)
                continue
            v = query_project(proj, rel, pkg)
            _projects.append(v)
            pass # pkgs
        if not args.project:
            args.project = ','.join(_projects)
        else:
            args.project += ','+','.join(_projects)
        pass
    
    # query for missing options
    print '-'*80
    for o in ('project', 'release', 'justification', 'savannah',):
        value = getattr(args, o)
        if value:
            print '%s : %s' % (o, value)
        else:
            setattr(args, o, query_option(o))
    print '-'*80

    args.project = args.project.split(',')
    args.release = args.release.split(',')
    if len(args.project) != len(args.release):
        raise RuntimeError(
            'Number of projects %s and releases %s do not match' %
            (args.project, args.release)
            )

    ok = False
    if valid_certificate():
        args.password = None
        choice = raw_input("Submit tag? [Y/n] ")      
        ok = len(choice)==0 or choice.upper()=="Y"
    else:
        # Get user name via env var or prompt
        if not args.user: args.user = os.environ.get("AMIUser",None) 
        if not args.user: args.user = os.environ.get("USER",None) 
        if not args.user: args.user = raw_input("AMI user name: ")
      
        if not args.password:
            args.password = getpass.getpass("Enter AMI password to submit: ")
        ok = len(args.password)>0

    if args.dry_run:
        client.dry_run = args.dry_run

    releases = args.release[:]
    projects = args.project[:]

    exitcode = 0
    if ok:
        # Submit tag request
        for p,rel,proj in zip(pkg_list, releases, projects):
            args.release = [rel]
            args.project = [proj]
            submit_tag(client, args,
                       p['packagePath']+p['packageName'],p['packageTag'])
    else:
        print "Tag submission aborted"
        exitcode = 1
        
    return exitcode

