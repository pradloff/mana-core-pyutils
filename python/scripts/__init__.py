# hook for PyUtils.scripts package

# FIXME: waiting for a proper declarative file
import PyUtils.acmdlib as acmdlib
acmdlib.register('chk-file', 'PyUtils.scripts.check_file:main')
acmdlib.register('diff-pool', 'PyUtils.scripts.diff_pool_files:main')
acmdlib.register('diff-root', 'PyUtils.scripts.diff_root_files:main')
acmdlib.register('dump-root', 'PyUtils.scripts.dump_root_file:main')
acmdlib.register('chk-sg', 'PyUtils.scripts.check_sg:main')
acmdlib.register('ath-dump', 'PyUtils.scripts.ath_dump:main')
acmdlib.register('chk-rflx', 'PyUtils.scripts.check_reflex:main')
acmdlib.register('gen-klass', 'PyUtils.scripts.gen_klass:main')
#acmdlib.register('tc.submit', 'PyUtils.AmiLib:tc_submit')
#acmdlib.register('tc.pkg-tree', 'PyUtils.AmiLib:tc_pkg_tree')
#acmdlib.register('ami-dset', 'PyUtils.AmiLib:ami_dset')

acmdlib.register('tc.find-pkg', 'PyUtils.scripts.tc_find_pkg:main')
acmdlib.register('tc.submit-tag', 'PyUtils.scripts.tc_submit_tag:main')
acmdlib.register('tc.show-clients', 'PyUtils.scripts.tc_show_clients:main')

acmdlib.register('get-tag-diff', 'PyUtils.scripts.get_tag_diff:main')

acmdlib.register('merge-files', 'PyUtils.scripts.merge_files:main')
acmdlib.register('filter-files', 'PyUtils.scripts.filter_files:main')

acmdlib.register('cmt.new-pkg', 'PyUtils.scripts.cmt_newpkg:main')
##

