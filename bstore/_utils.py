# -*- coding: utf-8 -*-
# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Private functions used by B-Store to facilitate its operation.

"""

import os
import ast, _ast
import bstore.config as cfg
import importlib

def findPlugins(classType):
    """Finds plugins of type `classType` inside modules of the plugins folder.
    
    Parameters
    ----------
    classType : str
        The name of the class to search for. A plugin represents a class.
        
    Returns
    -------
    plugins : list of tuple of (str, object)
        Each element is a tuple whose first element is the plugin name
        and whose second element is the class representing the plugin
        
    """
    pluginDir = os.path.expanduser(os.path.join(*cfg.__Plugin_Dir__))
    files = [file for file in os.listdir(pluginDir)
             if os.path.isfile(os.path.join(pluginDir, file))]
                 
    # Open files, read their source code, then parse the
    # source code into an AST from which classes may be read
    plugins = []
    for file in files:
        fullPath = os.path.join(pluginDir, file)
        with open(fullPath, 'r') as f:
            src = f.read()
            
        tree = ast.parse(src)
        classes = [cls for cls in tree.body
                   if isinstance(cls, _ast.ClassDef)
                   and cls.bases[0].attr == classType]
         
        # Import the module containing the plugin(s), then
        # import each plugin class
        mod = importlib.import_module(
            cfg.__Plugin_Dir__[-1] + '.' + os.path.splitext(file)[0])
        
        # Tuples are: (plugin name, plugin object)
        plugins.extend(((cls.name, getattr(mod, cls.name)) for cls in classes))
        
    return plugins
    