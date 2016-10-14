# -*- coding: utf-8 -*-

# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

from tkinter.messagebox import showerror

class CatchExceptions:
    """Decorator for catching exceptions in GUI functions.
    
    """
    def __init__(self, function):
        self.function = function

    def __call__(self, *args):
        try:
            return self.function(*args)
        except Exception as e:
            showerror(title = 'B-Store Error',
                      message = 'An error occurred in B-Store\n\n%s' % e)    
            print("Error: %s" % e)