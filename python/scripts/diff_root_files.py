# @file PyUtils.scripts.diff_root_files
# @purpose check that 2 ROOT files have same content (containers and sizes).
# @author Sebastien Binet
# @date February 2010

__version__ = "$Revision$"
__doc__ = "check that 2 ROOT files have same content (containers and sizes)."
__author__ = "Sebastien Binet"

### imports -------------------------------------------------------------------
import PyUtils.acmdlib as acmdlib
import PyUtils.RootUtils as ru
ROOT = ru.import_root()

### classes -------------------------------------------------------------------

### functions -----------------------------------------------------------------
@acmdlib.command(name='diff-root')
@acmdlib.argument('old',
                  help='path to the reference ROOT file to analyze')
@acmdlib.argument('new',
                  help='path to the ROOT file to compare to the reference')
@acmdlib.argument('-t', '--tree-name',
                  default='POOLCollectionTree',
                  help='name of the TTree to compare')
@acmdlib.argument('--ignore-leaves',
                  nargs='*',
                  default=('Token',),
                  help='set of leaves names to ignore from comparison')
@acmdlib.argument('--enforce-leaves',
                  nargs='*',
                  default=('BCID',),
                  help='set of leaves names we make sure to compare')
@acmdlib.argument('-v', '--verbose',
                  action='store_true',
                  default=False,
                  help="""Enable verbose printout""")
def main(args):
    """check that 2 ROOT files have same content (containers and sizes)
    """

    import PyUtils.RootUtils as ru
    root = ru.import_root()

    import PyUtils.Logging as L
    msg = L.logging.getLogger('diff-root')
    msg.setLevel(L.logging.INFO)

    msg.info('comparing tree [%s] in files:', args.tree_name)
    msg.info(' old: [%s]', args.old)
    msg.info(' new: [%s]', args.new)
    msg.info('ignore  leaves: %s', args.ignore_leaves)
    msg.info('enforce leaves: %s', args.enforce_leaves)

    fold = ru.RootFileDumper(args.old, args.tree_name)
    fnew = ru.RootFileDumper(args.new, args.tree_name)

    def tree_infos(tree, args):
        nentries = tree.GetEntriesFast()
        leaves = [l.GetName() for l in tree.GetListOfLeaves()
                  if l not in args.ignore_leaves]
        return {
            'entries' : nentries,
            'leaves': set(leaves),
            }
    
    def diff_tree(fold, fnew, args):
        infos = {
            'old' : tree_infos(fold.tree, args),
            'new' : tree_infos(fnew.tree, args),
            }

        nentries = min(infos['old']['entries'],
                       infos['new']['entries'])
        if infos['old']['entries'] != infos['new']['entries']:
            msg.info('different numbers of entries:')
            msg.info(' old: [%s]', infos['old']['entries'])
            msg.info(' new: [%s]', infos['new']['entries'])
            msg.info('=> comparing [%s] first entries...', nentries)
        msg.info('comparing over [%s] entries...', nentries)
        
        leaves = infos['old']['leaves'] & infos['new']['leaves']
        diff_leaves = infos['old']['leaves'] - infos['new']['leaves']
        if diff_leaves:
            msg.info('the following variables exist in only one tree !')
            for l in diff_leaves:
                msg.info(' - [%s]', l)
        leaves = leaves - set(args.ignore_leaves)
        
        msg.info('comparing [%s] leaves over [%s] entries...',
                 len(leaves), nentries)
        all_good = True
        n_good = 0
        n_bad = 0
        import collections
        from itertools import izip
        summary = collections.defaultdict(int)
        for d in izip(fold.dump(args.tree_name, nentries),
                      fnew.dump(args.tree_name, nentries)):
            tree_name, ientry, name, iold = d[0]
            _,              _,    _, inew = d[1]
            if (not (name[0] in leaves) or
                # FIXME: that's a plain (temporary?) hack
                name[-1] == "m_athenabarcode"):
                continue
            
            if d[0] == d[1]:
                diff = False
                n_good += 1
                continue
            n_bad += 1
            diff = True

            assert d[0][:-1] == d[1][:-1], \
                   "comparison iterators out of sync!\n%s != %s" % \
                   (d[0][:-1], d[1][:-1])
            
            n = '.'.join(map(str, ["%03i"%ientry]+name))
            diff_value = 'N/A'
            try:
                diff_value = 50.*(iold-inew)/(iold+inew)
                diff_value = '%.8f%%' % (diff_value,)
            except Exception:
                pass
            print '%s %r -> %r => diff= [%s]' %(n, iold, inew, diff_value)
            summary[name[0]] += 1

            if name[0] in args.enforce_leaves:
                msg.info("don't compare further")
                all_good = False
                break
            summary[name[0]] += 1
            pass # loop over events/branches
        
        msg.info('Found [%s] identical leaves', n_good)
        msg.info('Found [%s] different leaves', n_bad)

        keys = sorted(summary.keys())
        for n in keys:
            v = summary[n]
            msg.info(' [%s]: %i leaves differ', n, v)
            
        return n_bad
    
    ndiff = diff_tree(fold, fnew, args)
    if ndiff != 0:
        return 2
    return 0
