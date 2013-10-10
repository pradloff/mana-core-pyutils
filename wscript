# -*- python -*-

import waflib.Logs as msg

PACKAGE = {
    'name': 'Tools/PyUtils',
    'author': ['atlas collaboration'],
}

def pkg_deps(ctx):
    ctx.use_pkg('AtlasPolicy')
    ctx.use_pkg('External/AtlasPython')
    return

def configure(ctx):
    msg.debug ('[configure] package name: '+PACKAGE['name'])
    return

def build(ctx):



    ctx.build_pymodule(source=[
        'python/*.py',
        'python/AthFile',
        'python/scripts'])

    ctx.install_scripts(source=[
        'bin/*',
        ])

    for i in [
        ("checkFile", "checkFile.py"),
        ("checkSG",        "checkSG.py"),
        ("diffPoolFiles",  "diffPoolFiles.py"),
        ("merge-poolfiles",  "merge-poolfiles.py"),
        ("checkTag",       "checkTag.py"),
        ("setupWorkArea",  "setupWorkArea.py"),
        ("pyroot",         "pyroot.py"),
        ("print_auditor_callgraph",  "print_auditor_callgraph.py"),
        ("gen_klass",      "gen_klass.py"),
        ("build_cmt_pkg_db",  "build_cmt_pkg_db.py"),
        ("diffConfigs",    "diffConfigs.py"),
        ("vmem-sz	",     "vmem-sz.py"),
        ("dso-stats	",     "dso-stats.py"),
        ("dump-athfile",   "dump-athfile.py"),
        ("pkgco",          "pkgco.py"),
        ("icython",        "icython.py"),
        ("tabnanny-checker",  "tabnanny-checker.py"),
        ("get-tag-diff",   "get-tag-diff.py"),
        ("avn",            "avn.py"),
        ("abootstrap-wkarea",  "abootstrap-wkarea.py"),
        ("tc-submit-tag",  "tcSubmitTag.py"),
        ("tcSubmitTag",    "tcSubmitTag.py"),
        ("acmd",           "acmd.py"),
        ("diff-jobo-cfg",  "diff-jobo-cfg.py"),
        ("filter-and-merge-d3pd",  "filter-and-merge-d3pd.py"),
        ("diffTAGTree",    "diffTAGTree.py"),
        ]:
        dst, src = i[0], i[1]
        ctx.hwaf_declare_runtime_alias(dst, src)
        
    return
### EOF ###
