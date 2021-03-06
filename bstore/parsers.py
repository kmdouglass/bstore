# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016-2018
# See the LICENSE.txt file for more details.

import pathlib
from bstore import config
from abc import ABCMeta, abstractmethod, abstractproperty
from os.path import splitext
import importlib
import sys
import tkinter as tk
import bstore.database as db
import traceback
import warnings

__version__ = config.__bstore_Version__

"""Metaclasses
-------------------------------------------------------------------------------
"""


class Parser(metaclass=ABCMeta):
    """Translates SMLM files to machine-readable data structures.

    Attributes
    ----------
    dataset  : Dataset
        A Dataset object for insertion into a B-Store Datastore.
    requiresConfig : bool
        Does parser require configuration before use? This is primarily
        used by the GUI to determine whether the parser has attributes that
        are set by its __init__() method or must be set before parsing files.

    """

    def __init__(self):
        # Holds a parsed dataset.
        self._dataset = None

    @property
    def dataset(self):
        if self._dataset:
            return self._dataset
        else:
            raise ParserNotInitializedError('Error: There is currently no'
                                            'parsed dataset to return.')

    @dataset.setter
    def dataset(self, ds):
        self._dataset = ds

    @abstractproperty
    def requiresConfig(self):
        pass

    @abstractmethod
    def parseFilename(self):
        """Parses a file for conversion to a Dataset.

        """
        pass

"""
Concrete classes
-------------------------------------------------------------------------------
"""


class FormatMap(dict):
    """Two-way map for mapping one localization file format to another.

    FormatMap subclasses dict and acts like a two-way mapping between
    key-value pairs, unlike dict which provides only a one-way relationship.
    In the case where a key is missing, the dict returns the input key.
    This functionality greatly assists in converting header files for which
    no translation between column names is defined.

    To use this class, simply pass a dict to the FormatMap's constructor.
    Alternatively, create a FormatMap, which creates an empty dict. Then add
    fields as you wish.

    Parameters
    ----------
    init_dict : dict
        The dictionary to convert to a two-way mapping.

    References
    ----------
    [1] http://stackoverflow.com/questions/1456373/two-way-reverse-map

    """

    def __init__(self, init_dict=None):
        super(dict, self).__init__()

        # Populate the two-way dict if supplied
        if init_dict:
            for key, value in init_dict.items():
                self.__setitem__(key, value)

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        if value in self:
            del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __getitem__(self, key):
        try:
            val = dict.__getitem__(self, key)
        except KeyError:
            # If the key doesn't exist, then return the key. This
            # allows the use for pre-defined mappings between
            # header columns even when not all possible mappings
            # are defined.
            val = key

        return val

    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)

    def __len__(self):
        return dict.__len__(self) // 2


class PositionParser(Parser):
    """Reads a filename whose dataset IDs are determined by their positions.

    Parameters
    ----------
    positionIDs   : dict
        Integer/string pairs denoting the position in the filename
        (starting from zero on the left) and the ID field at that
        position. If a position should be skipped, set its value to None.
    sep           : str
        The character (or characters) that separate the different fields
        in the filename.

    Attributes
    ----------
    requiresConfig : bool
        Does parser require configuration before use?
    positionIDs    : dict
        Integer/string pairs denoting the position in the filename
        (starting from zero on the left) and the ID field at that
        position. If a position should be skipped, set its value to None.
    sep            : str
        The character (or characters) that separate the different fields
        in the filename.

    """

    def __init__(self, positionIDs={0: 'prefix', 1: 'acqID'}, sep='_'):
        super().__init__()
        self.positionIDs = positionIDs
        self.sep = sep

    @property
    def requiresConfig(self):
        return True

    def parseFilename(self, filename, datasetType='Localizations', **kwargs):
        """Converts a filename into a Dataset.

        Parameters
        ----------
        filename      : str or Path
            A string or pathlib Path object containing the dataset's filename.
        datasetType   : str
            The type of the dataset being parsed. This tells the Parser
            how to interpret the data.

        """
        self.dataset = None

        # Check for a valid datasetType
        if datasetType not in config.__Registered_DatasetTypes__:
            raise DatasetTypeError(('{} is not a registered '
                                    'type.').format(datasetType))

        try:
            # Save the full path to the file for later.
            # If filename is already a Path object, this does nothing.
            self._fullPath = pathlib.Path(filename)

            # Remove file type ending and any parent folders
            # Example: 'path/to/HeLa_Control_7.csv' becomes 'HeLa_Control_7'
            #rootName = splitext(filename)[0].split('/')[-1]
            rootName = str(self._fullPath.stem)

            # Extract the ids
            idDict = self._parse(rootName)

            mod = importlib.import_module('bstore.datasetTypes.{0:s}'.format(
                datasetType))
            dType = getattr(mod, datasetType)
            self.dataset = dType(datasetIDs=idDict)

            # Read the data from file
            self.dataset.data = self.dataset.readFromFile(
                self._fullPath, **kwargs)
        except:
            if config.__Verbose__:
                print(traceback.format_exc())
            raise ParseFilenameFailure('ParseFilenameError')

    def _parse(self, rootName):
        """Actually does the work of splitting the name and finding IDs.

        rootName : str
            The actual string to parse.

        Returns
        -------
        idDict : dict
            The Dataset ids extracted from the filename.

        """
        idDict = {}
        fields = rootName.split(self.sep)

        if max(self.positionIDs.keys()) + 1 > len(fields):
            # Raises an error if more fields are supplied than are present in
            # the filename.
            raise ParseFilenameFailure('ParseFilenameError')

        for pos, field in enumerate(fields):
            # Skip empty or positions or those marked None
            if pos not in self.positionIDs or self.positionIDs[pos] is None:
                continue
            else:
                try:
                    # Convert numeric fields to numeric types
                    idDict[self.positionIDs[pos]] = int(field)
                except ValueError:
                    idDict[self.positionIDs[pos]] = field

        return idDict

    """
    Parser GUI functionality
    ------------------------
    """

    def gui(self, parent):
        """Configure the parser for the GUI interface.

        Parameters
        ----------
        parent : tkinter.Tk object
            The parent window for this dialog.

        """
        # Used to determine what to return when OK or Cancel
        # buttons are clicked.
        self._configuredByGUI = False

        dsIDs = db.DatasetID._fields  # Extract dataset ID names
        options = [x for x in dsIDs
                   if x != 'datasetType' and x != 'attributeOf']
        options.append('field separator')

        top = tk.Toplevel(master=parent)
        top.title('PositionParser Configuration')
        tk.Grid.rowconfigure(top, 0, weight=1)
        tk.Grid.columnconfigure(top, 0, weight=1)

        # Set the field positions in the filename
        fields = self._GUI_Frame_PositionIDs(master=top, padx=5, pady=5,
                                             text='Dataset IDs',
                                             positionIDs=self.positionIDs)
        fields.grid(row=0, columnspan=2)

        # Set the field separator character
        sep = self._GUI_Frame_Separator(master=top, padx=5, pady=5,
                                        text='Fields separator',
                                        separator=self.sep)
        sep.grid(row=1, columnspan=2)

        # Exit this window by clicking OK or Cancel;
        # OK updates the parser's state whereas Cancel does not
        ok = tk.Button(master=top, text='OK',
                       command=lambda: self._guiSet(fields.fields,
                                                    sep.sep, top))
        cancel = tk.Button(master=top, text='Cancel',
                           command=top.destroy)
        ok.grid(row=2, column=0, sticky=tk.E)
        cancel.grid(row=2, column=1, sticky=tk.W)

    def _guiSet(self, fields, sep, top):
        """Sets the Parser attributes based on the GUI inputs.

        Parameters
        ----------
        fields : dict of str:tk.Entry
        sep    : tk.Entry
        top    : tk.Tkinter object

        """
        self.positionIDs = {int(entry.get()): fieldname
                            for fieldname, entry in fields.items()
                            if entry.get()}
        self.sep = sep.get()
        self._configuredByGUI = True
        top.destroy()

    class _GUI_Frame_PositionIDs(tk.LabelFrame):
        """Defines the frame of the GUI configuration for dataset IDs.

        Attributes
        ----------
        fields : dict of str:tk.Entry

        """

        def __init__(self, positionIDs={}, **kwargs):
            super().__init__(**kwargs)
            self.positionIDs = positionIDs

            dsIDs = db.DatasetID._fields  # Extract dataset ID names
            options = [x for x in dsIDs
                       if x != 'datasetType' and x != 'attributeOf']

            directions = ('Enter an integer starting from zero that '
                          'corresponds to the position of each ID field '
                          'in the filename.\n\nExample: If prefix is at '
                          'position 0, acqID is at position 2, and the '
                          'separator is \'_\', then the filename '
                          'HeLa_Cells_35.csv will be understood to have '
                          '\'HeLa\' as its prefix and \'35\' as its acqID. '
                          '\'Cells\' will not be used.\n\nLeave fields empty '
                          'if they should not be assigned any values. '
                          '(\'prefix\' and \'acqID\' must be assigned.)')
            d = tk.Label(self, text=directions,
                         wraplength=300, justify=tk.LEFT)
            d.grid(row=0, column=0, columnspan=2)

            # Add the labels and entries for each field ID integer
            self.fields = {}
            for index, name in enumerate(options):
                tk.Label(self, text=name).grid(row=index + 1, column=0,
                                               sticky=tk.W)
                e = tk.Entry(self)
                e.grid(row=index + 1, column=1, sticky=tk.E)

                # Set the values of the text fields to the current state of
                # the instance.
                if name in self.positionIDs.values():
                    td = self.positionIDs
                    # Gets the keys corresponding to a particular value
                    posNum = list(td.keys())[list(td.values()).index(name)]
                    e.insert(0, str(posNum))
                self.fields[name] = e

    class _GUI_Frame_Separator(tk.LabelFrame):
        """Defines the frame of the GUI configuration for the field separator.

        Attributes
        ----------
        sep : tk.Entry

        """

        def __init__(self, separator='', **kwargs):
            super().__init__(**kwargs)

            directions = ('Enter a character that separates the fields in '
                          'the filename. This will typically be an underscore '
                          '\'_\' or a hyphen \'-\', but may also be a '
                          'combination of characters, such as \'_-\'.')
            d = tk.Label(self, text=directions,
                         wraplength=300, justify=tk.LEFT)
            d.grid(row=0, column=0, columnspan=2)

            tk.Label(self, text='separator').grid(row=1, column=0,
                                                  sticky=tk.W)
            self.sep = tk.Entry(self)
            self.sep.grid(row=1, column=1, sticky=tk.E)
            self.sep.insert(0, separator)


class SimpleParser(Parser):
    """A simple parser for extracting acquisition information.

    The SimpleParser converts files of the format prefix_acqID.* into
    Datasets for insertion into a datastore. * represents filename
    extensions like .csv, .json, and .tif.

    Attributes
    ----------
    requiresConfig : bool
        Does parser require configuration before use?

    """
    @property
    def requiresConfig(self):
        return False

    def parseFilename(self, filename, datasetType='Localizations', **kwargs):
        """Converts a filename into a Dataset.

        Parameters
        ----------
        filename      : str or Path
            A string or pathlib Path object containing the dataset's filename.
        datasetType   : str
            The type of the dataset being parsed. This tells the Parser
            how to interpret the data.

        """
        # Resets the parser
        self.dataset = None

        # Check for a valid datasetType
        if datasetType not in config.__Registered_DatasetTypes__:
            raise DatasetTypeError(('{} is not a registered '
                                    'type.').format(datasetType))

        try:
            # Save the full path to the file for later.
            # If filename is already a Path object, this does nothing.
            self._fullPath = pathlib.Path(filename)

            # Convert Path objects to strings if Path is supplied
            if isinstance(filename, pathlib.PurePath):
                filename = str(filename.name)

            # Remove file type ending and any parent folders
            # Example: 'path/to/HeLa_Control_7.csv' becomes 'HeLa_Control_7'
            rootName = splitext(filename)[0].split('/')[-1]

            # Extract the prefix and acqID
            prefix, acqID = rootName.rsplit('_', 1)
            acqID = int(acqID)

            # Build the return dataset
            idDict = {'prefix': prefix, 'acqID': acqID}

            mod = importlib.import_module(
                'bstore.datasetTypes.{0:s}'.format(datasetType))
            dType = getattr(mod, datasetType)
            self.dataset = dType(datasetIDs=idDict)

            # Read the data from file
            self.dataset.data = self.dataset.readFromFile(
                self._fullPath, **kwargs)
        except:
            self.dataset = None
            raise ParseFilenameFailure(('Error: File could not be parsed.',
                                        sys.exc_info()[0]))

"""
Exceptions
-------------------------------------------------------------------------------
"""


class DatasetTypeError(Exception):
    """Error raised when a bad datasetTypeName is passed to Parser.

    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ParseFilenameFailure(Exception):
    """Raised when Parser fails to parser a filename.

    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ParserNotInitializedError(Exception):
    """ Raised when Parser is requested to return data but is not initialized.

    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
