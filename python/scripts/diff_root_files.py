# @file PyUtils.scripts.diff_root_files
# @purpose check that 2 ROOT files have same content (containers and sizes).
# @author Sebastien Binet
# @date February 2010

__version__ = "$Revision$"
__doc__ = "check that 2 ROOT files have same content (containers and sizes)."
__author__ = "Sebastien Binet"


### imports -------------------------------------------------------------------
import PyUtils.acmdlib as acmdlib

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
    
    fold = root.TFile.Open(args.old)
    if (fold is None or
        not isinstance(fold, root.TFile) or
        not fold.IsOpen()):
        msg.error('could not open [%s]', args.old)
        return 1
    
    fnew = root.TFile.Open(args.new)
    if (fnew is None or
        not isinstance(fnew, root.TFile) or
        not fnew.IsOpen()):
        msg.error('could not open [%s]', args.new)
        return 1

    old_tree = fold.Get(args.tree_name)
    if old_tree is None or not isinstance(old_tree, root.TTree):
        msg.error('no tree [%s] in file [%s]', args.tree_name, args.old)
        return 1

    new_tree = fnew.Get(args.tree_name)
    if new_tree is None or not isinstance(new_tree, root.TTree):
        msg.error('no tree [%s] in file [%s]', args.tree_name, args.new)
        return 1

    def tree_infos(tree, args):
        nentries = tree.GetEntriesFast()
        leaves = [l.GetName() for l in tree.GetListOfLeaves()
                  if l not in args.ignore_leaves]
        return {
            'entries' : nentries,
            'leaves': set(leaves),
            }
    
    def diff_tree(old_tree, new_tree, args):
        infos = {
            'old' : tree_infos(old_tree, args),
            'new' : tree_infos(new_tree, args),
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

        msg.info('comparing [%s] leaves over [%s] entries...',
                 len(leaves), nentries)
        all_good = True
        n_good = 0
        n_bad = 0
        import collections
        summary = collections.defaultdict(int)
        for i in xrange(nentries):
            if old_tree.GetEntry(i) < 0:
                msg.error(
                    'could not load entry [%s] from tree [%s] (file=%s)',
                    i, args.tree_name, args.old)
                all_good = False
                break
            if new_tree.GetEntry(i) < 0:
                msg.error(
                    'could not load entry [%s] from tree [%s] (file=%s)',
                    i, args.tree_name, args.new)
                all_good = False
                break

            diff = False
            for name in leaves:
                old_val = getattr(old_tree, name)
                new_val = getattr(new_tree, name)
                if old_val != new_val:
                    diff = True
                    msg.info('Event #%4i difference [%s]', i, name)
                    msg.info(' old: %s', old_val)
                    msg.info(' new: %s', new_val)
                    diff_value = 'N/A'
                    try:
                        diff_value = 50.*(old_val-new_val)/(old_val+new_val)
                        diff_value = '(%.3f%%)' % (diff_value,)
                    except Exception:
                        pass
                    msg.info(' => diff: [%s]', diff_value)

                    if name in args.enforce_leaves:
                        msg.info("don't compare further")
                        all_good = False
                        break
                    summary[name] += 1
                pass # loop over leaves
            
            if diff:
                n_bad += 1
            else:
                n_good += 1

            pass # loop over events
        
        msg.info('Found [%s] identical events', n_good)
        msg.info('Found [%s] different events', n_bad)

        for n,v in summary.iteritems():
            msg.info(' [%s]: %i events differ', n, v)
            
        return n_bad
    
    ndiff = diff_tree(old_tree, new_tree, args)
    return ndiff
