# @file PyUtils/python/AthFile/__init__.py
# @purpose a simple abstraction of a file to retrieve informations out of it
# @author Sebastien Binet <binet@cern.ch>
# @date October 2008
from __future__ import with_statement

__doc__ = "a simple abstraction of a file to retrieve informations out of it"
__version__ = "$Revision$"
__author__  = "Sebastien Binet <binet@cern.ch>"

### imports -------------------------------------------------------------------
import os
import imp
import hashlib

__all__        = []
__pseudo_all__ = [
    'AthFile',
    'ftype',
    'fopen',
    'exists',
    'server',
    ]

import PyUtils.Decorators as _decos
import impl as _impl
import tests as _tests
AthFile = _impl.AthFile

### classes -------------------------------------------------------------------
import types
class ModuleFacade(types.ModuleType):
    """a helper class to manage the instantiation of the ``AthFileMgr`` and
    ``AthFileServer`` objects and allow attribute-like access to methods
    (stolen from PyRoot)
    """
    def __init__( self, module ):
        types.ModuleType.__init__(self, module.__name__)
        self.__dict__['module'] = module
        self.__dict__[ '__doc__'  ] = module.__doc__
        self.__dict__[ '__name__' ] = module.__name__
        self.__dict__[ '__file__' ] = module.__file__

        self.__dict__['_tests'] = _tests
        self.__dict__['_impl']  = _impl
        self.__dict__['_guess_file_type'] = _guess_file_type
        
        import atexit
        atexit.register(self.shutdown)
        del atexit
        
    def __getattr__(self, k):
        if k in self.__dict__:
            return self.__dict__.get(k)
        if k.startswith('__'):
            return types.ModuleType.__getattribute__(self, k)
        return object.__getattribute__(self, k)
    
    @property
    def server(self):
        if '_server' not in self.__dict__:
            if imp.lock_held():
                raise RuntimeError('cannot create an AthFile server while '
                                   'a module is being imported...\n'
                                   'this is a fundamental limitation. please '
                                   'fix your joboptions.py file')
            _srv = self.__dict__['_server'] = self._mgr.Server()
            import os
            _orig_setenv = self.__dict__['_old_os_setenv'] = os.environ.__setitem__
            def _setenv(k, v):
                """monkey patch os.environ.__setitem__ to transfer
                the master process environment with the AthFileServer's one
                """
                _srv._setenv(k,v)
                return _orig_setenv(k,v)
            os.environ.__setitem__ = _setenv
            
        server = self.__dict__['_server']
        if server._manager._state.value == server._manager._state.SHUTDOWN:
            raise RuntimeError('AthFileServer already shutdown')
        return server

    def restart_server(self):
        server = self.__dict__['_server']
        assert server._manager._state.value == server._manager._state.SHUTDOWN, \
               "invalid server state (%s)" % (server._manager._state.value,)
        del self.__dict__['_server']
        del self.__dict__['_mgr_impl']
        return self.server
    
    @property
    def _mgr(self):
        if '_mgr_impl' not in self.__dict__:
            mgr = self._impl.AthFileMgr()
            mgr.start()
            self.__dict__['_mgr_impl'] = mgr
        return self.__dict__['_mgr_impl']

    @_decos.memoize
    def shutdown(self):
        if '_server' in self.__dict__:
            #self.msg.info('shutting down athfile-server...')
            try:
                self.server._cleanup_pyroot()
            except Exception:
                pass
            # restore the original os.environ.__setitem__ method
            os.environ.__setitem__ = self.__dict__['_old_os_setenv']
            del self.__dict__['_old_os_setenv']
            return self._mgr.shutdown()
        return
    
    @property
    def msg(self):
        return self.server.msg()
    
    @property
    def cache(self):
        return self.server.cache()

    @property
    def save_cache(self):
        return self.server.save_cache

    @property
    def load_cache(self):
        return self.server.load_cache

    @property
    def flush_cache(self):
        return self.server.flush_cache
    
    @property
    def ftype(self):
        return self.server.ftype

    @property
    def fname(self):
        return self.server.fname

    @property
    def exists(self):
        return self.server.exists

    @property
    def tests(self):
        return self._tests
    
    def fopen(self, fnames, evtmax=1):
        """
        helper function to create @c AthFile instances
        @param `fnames` name of the file (or a list of names of files) to inspect
        @param `nentries` number of entries to process (for each file)
        
        Note that if `fnames` is a list of filenames, then `fopen` returns a list
        of @c AthFile instances.
        """
        if isinstance(fnames, (list, tuple)):
            return [self.server.fopen(fname, evtmax) for fname in fnames]
        return self.server.fopen(fnames, evtmax)

    ## def __del__(self):
    ##     self._mgr.shutdown()
    ##     return super(ModuleFacade, self).__del__()
    
    pass # class ModuleFacade

###

def _guess_file_type(fname, msg):
    """guess the type of an input file (bs,rdo,esd,aod,...)
    """
    input_type = None
    import PyUtils.AthFile as af
    try:
        file_type,file_name = af.ftype(fname)
    except Exception:
        raise # for now
    if file_type == 'bs':
        input_type = 'bs'
    elif file_type == 'pool':
        import PyUtils.PoolFile as pf
        stream_names = pf.extract_stream_names(fname)
        stream_names = [s.lower() for s in stream_names]
        if len(stream_names) > 1:
            msg.warning('got many stream names: %r', stream_names)
            msg.warning('only considering the 1st one...')
        elif len(stream_names) <= 0:
            msg.warning('got an empty list of stream names')
            raise SystemExit(1)
        stream_name = stream_names[0]
        input_type = {
            'stream1':    'rdo',
            'streamesd' : 'esd',
            'streamaod' : 'aod',
            # FIXME: TODO: TAG, DPD
            }.get(stream_name, 'aod')

    else:
        msg.error('unknown file type (%s) for file [%s]',
                  file_type, file_name)
    return input_type


### exec at import ------------------------------------------------------------
import sys
sys.modules[ __name__ ] = ModuleFacade( sys.modules[ __name__ ] )
del ModuleFacade
