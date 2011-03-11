# @file timerdecorator.py
# @purpose decorate functions which will have a limited alloted time to finish execution
# @date February 2011
# ripped off from:
#   http://code.activestate.com/recipes/483752/

import sys
import threading

class TimeoutError(Exception):
    pass

def timelimit(timeout):
    def internal(function):
        def internal2(*args, **kw):
            class Calculator(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None
                
                def run(self):
                    try:
                        self.result = function(*args, **kw)
                    except:
                        self.error = sys.exc_info()[0]
            
            c = Calculator()
            c.start()
            c.join(timeout)
            if c.isAlive():
                raise TimeoutError
            if c.error:
                raise c.error
            return c.result
        return internal2
    return internal
