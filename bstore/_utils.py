# -*- coding: utf-8 -*-
# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

"""Private functions used by B-Store to facilitate its operation.

"""

import os
import ast
import _ast
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
                   and cls.bases]  # Remove classes that don't inherit anything

        # Remove all classes who don't inherit from classType; this requires
        # checking for the presence of an id attribute OR an attr attribute
        # in cls.bases that equals the string in classType
        fClasses = _filterClassBases(classes, classType)

        # Import the module containing the plugin(s), then
        # import each plugin class
        mod = importlib.import_module(
            cfg.__Plugin_Dir__[-1] + '.' + os.path.splitext(file)[0])

        # Tuples are: (plugin name, plugin object)
        plugins.extend(((cls.name, getattr(mod, cls.name))
                        for cls in fClasses))

    return plugins


def _filterClassBases(classes, match):
    """Filters a list of AST classes.

    Classes whose ast.ClassDef.id or astClassDef.attr attributes do not
    match the 'match' string input are removed.

    Parameters
    ----------
    classes  : list of ast.ClassDef objects
    match    : str
        The string to match to ast.ClassDef.id or ast.ClassDef.base

    Returns
    -------
    rClasses : list of ast.ClassDef objects
        The filtered list of classes whose id or attr base attributes match
        the string in the `match` variable.

    """
    rClasses = []
    for cls in classes:
        # First check the id field
        try:
            if match in (base.id for base in cls.bases):
                rClasses.append(cls)
        except AttributeError:
            pass

        # Now check for attributes
        try:
            if match in (base.attr for base in cls.bases):
                rClasses.append(cls)
        except AttributeError:
            continue

    return rClasses
