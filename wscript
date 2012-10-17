# -*- python -*-

import waflib.Logs as msg

PACKAGE = {
    'name': 'Tools/PyUtils',
    'author': ['atlas collaboration'],
}

def pkg_deps(ctx):
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
        'bin/*.py',
        ])

    return
### EOF ###
