# @file PyUtils.scripts.tc_show_clients
# @purpose show the clients of a package using TC-2
# @author Sebastien Binet
# @date May 2011

__version__ = "$Revision$"
__doc__ = "show the clients of a package using TC-2"
__author__ = "Sebastien Binet"


### imports -------------------------------------------------------------------
import PyUtils.acmdlib as acmdlib

@acmdlib.command(name='tc.show-clients')
@acmdlib.argument('pkg',
                  nargs='+',
                  help='(list of) package(s) to show clients of')
@acmdlib.argument('-r', '--release',
                  required=True,
                  help='the release in which to show the clients (e.g: 17.0.1)')
@acmdlib.argument('--co',
                  action='store_true',
                  default=False,
                  help='enable the checkout of these clients')
def main(args):
    """show the clients of a package using TC-2"""

    import PyUtils.AmiLib as amilib
    client = amilib.Client()

    pkgs = args.pkg
    if isinstance(pkgs, basestring):
        pkgs = [pkgs]

    all_clients = []
    for pkg in pkgs:
        print
        client.msg.info('showing clients of [%s]...', pkg)
        # find the project for this pkg
        projects = client.get_project_of_pkg(pkg, args.release)
        pkg = client.find_pkg(pkg, check_tag=False)
        fpkg = pkg['packagePath']+pkg['packageName']
        if len(projects) > 1:
            client.msg.info('pkg [%s] exists in more than 1 project: %s ==> will use last one')
        project = projects[-1]
        clients = client.get_clients(project, args.release, fpkg)
        for n,v in clients:
            print n, v
            if ('-%s-'%project not in v) and v not in all_clients:
                all_clients.append(v)
        #client.msg.info('        tag= [%s]', tag)

    rc = 0
    if args.co:
        print
        client.msg.info(":"*40)
        client.msg.info(":: list of package versions to checkout:")
        for c in all_clients:
            print c
        cmd = ['pkgco.py',]+all_clients
        import subprocess
        rc = subprocess.call(cmd)
    return rc

