# @file PyUtils.scripts.tc_find_tag
# @purpose Find package version taking into account project dependencies
# @author Frank Winklmeier
# @date Novemeber 2011

__version__ = "$Revision:$"
__doc__ = "Find package version taking into account project dependencies."
__author__ = "Frank Winklmeier"


### imports -------------------------------------------------------------------
import PyUtils.acmdlib as acmdlib

@acmdlib.command(name='tc.find-tag')
@acmdlib.argument(
    'pkg',
    nargs='+',
    help='(list of) package(s) to find in TagCollector')
@acmdlib.argument(
    '-p', '--project',
    action='store',
    required=True,
    help='Project')
@acmdlib.argument(
    '-r', '--release',
    action='store',
    help='Release [default: latest]')

def main(args):
    """find package version taking into account project dependencies"""

    import PyUtils.AmiLib as amilib
    client = amilib.Client()

    pkgs = args.pkg
    if isinstance(pkgs, basestring):
        pkgs = [pkgs]

    if not args.release:
        rel = client.get_releases(args.project)
        if len(rel)==0:
            raise RuntimeError('No release for project',args.project)
        args.release = rel[-1]

    client.msg.info('searching package tags for [%s] in release [%s]' % (','.join(pkgs),args.release))
    pkg_list = [client.get_version_of_pkg_with_deps(pkg, args.project, args.release) for pkg in pkgs]
    pkg_list = sum(pkg_list,[])   # Flatten list in case more than one version per package
    client.msg.info('Found %d package(s)' % len(pkg_list))
    for p in pkg_list:
        print(' '.join(p))

    return 0

