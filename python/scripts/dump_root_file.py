# @file PyUtils.scripts.dump_root_file
# @purpose ascii-fy a ROOT file
# @author Sebastien Binet
# @date December 2010

__version__ = "$Revision$"
__doc__ = "ASCII-fy a ROOT file"
__author__ = "Sebastien Binet"


### imports -------------------------------------------------------------------
import PyUtils.acmdlib as acmdlib

@acmdlib.command(name='dump-root')
@acmdlib.argument('fname',
                  help='path to the ROOT file to dump')
@acmdlib.argument('-t', '--tree-name',
                  default=None,
                  help='name of the TTree to dump (default:all)')
@acmdlib.argument('-v', '--verbose',
                  action='store_true',
                  default=False,
                  help="""Enable verbose printout""")
def main(args):
    """check that 2 ROOT files have same content (containers and sizes)
    """

    import PyUtils.RootUtils as ru
    root = ru.import_root()

    _inspect = root.RootUtils.PyROOTInspector.pyroot_inspect2

    import PyUtils.Logging as L
    msg = L.logging.getLogger('dump-root')
    msg.setLevel(L.logging.INFO)

    msg.info('fname: [%s]', args.fname)
    root_file = root.TFile.Open(args.fname)
    if (root_file is None or
        not isinstance(root_file, root.TFile) or
        not root_file.IsOpen()):
        msg.error('could not open [%s]', args.fname)
        return 1

    tree_names = []
    if args.tree_name:
        tree_names = list(args.tree_name)
    else:
        tree_names = []
        keys = [k.GetName() for k in root_file.GetListOfKeys()]
        for k in keys:
            o = root_file.Get(k)
            if isinstance(o, root.TTree):
                tree_names.append(k)
                
    msg.info('dumping trees:  %s', tree_names)

    rc = 0
    for tree_name in tree_names:
        f = ru.RootFileDumper(args.fname, tree_name)
        nentries = f.tree.GetEntries()
        for d in f.dump(tree_name, nentries):
            tree_name, ientry, name, data = d
            n = '.'.join(map(str, [tree_name,"%03i"%ientry]+name))
            print '%s %r' %(n, data)
    return 0
