"""Creates the HDF Datastore build dialog window.

"""

# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

from tkinter import Entry, LabelFrame, Checkbutton, Grid, IntVar, Radiobutton
from tkinter import Scrollbar, Text, BooleanVar, Label, E, W, DISABLED, END
from tkinter import Toplevel, Button, N, S, StringVar
from tkinter.filedialog import askdirectory, asksaveasfilename
from tkinter.messagebox import showinfo

from pathlib import Path

import bstore.config as cfg
import bstore.database as db
import bstore.datasetTypes as dsTypes
import bstore.parsers as parsers
import bstore._utils as _utils
import bstore.gui._guiutils as _guiutils

import ast
import inspect
import threading
import webbrowser

miscURL = 'http://b-store.readthedocs.io/en/development/quickstart.html#misc-build-options'

def openMiscHelp():
    webbrowser.open_new(miscURL)

class CreateHDFDatastore():
    """Dialog for creating a new HDFDatastore object.
    
    Parameters
    ----------
    root : tkinter.Tk() object
        The calling application window.
    
    """
    def __init__(self, root):
        top = Toplevel(master = root)
        top.title('Create a new HDF Datastore')
        frames = {'SelectFilename'     : 4,
                  'SelectDatasetTypes' : 1,
                  'SelectSearchPath'   : 0,
                  'SelectParser'       : 2,
                  'Options'            : 3,
                  'BuildButton'        : 5}
        Grid.rowconfigure(top, frames['SelectDatasetTypes'], weight = 1)
        Grid.rowconfigure(top, frames['BuildButton'],        weight = 0)
        Grid.columnconfigure(top, 0, weight=1)
        
        # Select dataset types
        t = self.Frame_SelectDatasetTypes(
            master = top, padx = 5, pady = 5,
            text = 'Select dataset types and their corresponding files')
        t.grid(row = frames['SelectDatasetTypes'], sticky = N+S+E+W)
        
        # Select search path
        s = self.Frame_SelectSearchPath(
            master = top, padx = 5, pady = 5,
            text = 'Directory containing input data files')
        s.grid(row = frames['SelectSearchPath'], sticky = E+W)
        
        # Select parser
        p = self.Frame_SelectParser(
            master = top, padx = 5, pady = 5,
            text = 'Select and configure the filename parser')
        p.grid(row = frames['SelectParser'], sticky = E+W)
        
        # Optional arguments for readingFromFiles
        o = self.Frame_SelectOptions(
            master = top, padx = 5, pady = 5,
            text = 'Miscellaneous build options')
        o.grid(row = frames['Options'], sticky = E+W)
        
        # Select filename and path    
        f = self.Frame_SelectFilename(
            master = top, padx = 5, pady = 5,
            text = 'Path and filename for the new datastore')
        f.grid(row = frames['SelectFilename'], sticky = E+W)        
        
        frameParams = (f, t, s, p, o)
        build = Button(
            master = top, text = 'Build',
            command=lambda: self._buildDatabase(self, top, frameParams))
        build.grid(row = frames['BuildButton'])
        
        # Make this window modal
        top.transient(root)
        top.grab_set()
        root.wait_window(top)
        
    @_guiutils.CatchExceptions
    def _buildDatabase(self, top, frames):
        """Build the database by taking data from the GUI frames.
        
        The o_ preceding the argument names refers to the fact that the
        arguments are Frame OBJECTS and thus their data is contained in
        their attributes.
        
        Parameters
        ----------
        top    : tkinter.TopLevel
        frames : tuple of tkinter.LabelFrame
        o_filename     : tkinter LabelFrame
        o_datasetTypes : tkinter LabelFrame
        o_searchPath   : tkinter LabelFrame
        o_parser       : tkinter LabelFrame
        o_options      : tkinter LabelFrame
        
        """
        o_filename, o_datasetTypes, o_searchPath, o_parser, o_options = frames
        filenameStrings = o_datasetTypes.get() 
        if cfg.__Verbose__:
            print('Filename: ' + str(o_filename.filename.get()))
            print('Dataset Types: ' + str(filenameStrings))
            print('Search Path: ' + str(o_searchPath.searchPath.get()))
            print('Parser: ' + str(o_parser.parser))
            print(('Options: ' +
                   str(o_options.kwargs)))
            
            try:        
                print(('Configured by GUI? '+ 
                       str(o_parser.parser._configuredByGUI)))
                print('Position IDs: ' + str(o_parser.parser.positionIDs))
                print(('Separator: ' + 
                       str(o_parser.parser.sep)))
            except:
                pass

        assert o_searchPath.isReady, ('Error: Search path for input '
                                      'files is not set.')           
        assert o_filename.isReady, 'Error: Path to new Datastore is not set.'
        
        if not Path(o_searchPath.searchPath.get()).exists():
            raise db.SearchDirectoryDoesNotExist(
                '%s does not exist.' % str(o_searchPath.searchPath.get()))
        
        # Register the dataset types
        cfg.__Registered_DatasetTypes__ = [
            x for x in filenameStrings.keys()]
        
        # Open a dialog indicating the build is occurring
        showinfo(
            title = 'Build datastore',
            message = ('Starting datastore build...\nThis may take a '
                       'few minutes for large datasets (> 10 GB).'),
            parent = top)     
                 
        # Start the build thread that creates the Datastore
        with db.HDFDatastore(o_filename.filename.get()) as dstore:
        
            t = threading.Thread(
                target = dstore.build,
                args = (
                    o_parser.parser, o_searchPath.searchPath.get(),
                    filenameStrings),
                kwargs  = o_options.kwargs)
                
            bd = self.BuildDialog(top, t)
            bd.start()
            bd.destroy()
        
        showinfo(title   = 'Build Complete',
                 message = ('The build has finished.'))
                 
    """CreateHDFDatastore Dialogs
    ---------------------------------------------------------------------------
    """
    class BuildDialog():
        """Indicates the build status of a datastore.
        
        Parameters
        ----------
        parent : tkinter.Toplevel
        thread : threading.Thread
        
        """
        def __init__(self, parent, thread):
            win = Toplevel(master = parent)
            win.title('Please wait...')
            
            self._parent = parent
            self._thread = thread
            self._win = win
            
            msg  = Label(
                master = win,
                text = ('Building datastore... Please wait until '
                        'build is complete.'))
                
            msg.pack()
            
        def start(self):
            # Don't start unless the "Please wait" window is visible
            self._parent.wait_visibility(self._win)
            
            # Start build thread
            self._thread.start()
            self._thread.join()
            
        def destroy(self):
            self._win.destroy()

    """CreateHDFDatastore Frames
    ---------------------------------------------------------------------------
    """            
    class Frame_SelectDatasetTypes(LabelFrame):
        """Select the dataset types to include in the database.
        
        References
        ----------
        .. [1] http://stackoverflow.com/questions/5860675/variable-size-list-of-checkboxes-in-tkinter
        
        """        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._isReady = True
            
            self.vsb  = Scrollbar(self, orient="vertical")
            self.text = Text(
                self, height = 10,
                yscrollcommand=self.vsb.set,
                bg = self.master.cget('bg'),
                wrap = 'word')
            self.vsb.config(command=self.text.yview)
            self.vsb.pack(side='right', fill='y')
            self.text.pack(side='left', fill='both', expand=True)
            
            # Create the list of checkboxes
            self._listOfTypes = []
            for currType in dsTypes.__all__:
                v = BooleanVar(value = 1)
                cb = Checkbutton(self, text = '%s' % currType, anchor = W,
                                 width = 15, variable = v)
                cb.var = v # Easy access to checkbox's current value
                
                e  = Entry(self)
                e.delete(0, END)
                e.insert(0, '<suffix>.<file_extension>')
                
                self._listOfTypes.append((cb, e))
                self.text.window_create('end', window=cb)
                self.text.window_create('end', window=e)
                self.text.insert('end', '\n') # Forces one checkbox per line
            
            # Insert help message
            self.text.insert('end', self.__doc__)
            
            # This MUST follow insertion and positioning of
            # the checkboxes/entries
            self.text.config(state = DISABLED)
        
        @property
        def __doc__(self):
            doc = ('\nSelect the types of datasets to include and specify '
                   'the corresponding naming patterns for their input files. '
                   'For example, if your localization files follow the '
                   'naming convention <condition>_<fov_num>_locs.csv, then '
                   'enter \'_locs.csv\' (without the quotes) in the text '
                   'box next to Localizations.\n\nYou may use the asterik '
                   'symbol (*) as a wildcard. For example, if the convention '
                   'for localization files was instead <condition>_locs_<fov'
                   '_num>.csv, then enter _locs*.csv in the text box next to '
                   'Localizations. Everything after the \'*\' will be '
                   'included in the search pattern.')
            return doc
        
        @property
        def isReady(self):
            return self._isReady
        
        def get(self):
            """Returns information about the frame.
            
            Returns
            -------
            filenameStrings : dict
                Key-value pairs of the dataset types and their filename
                suffixes.
                
            """
            filenameStrings = {k.cget('text') : v.get()
                                   for k, v in self._listOfTypes
                                   if k.var.get() and v.get()
                              }
            return filenameStrings
            
    class Frame_SelectFilename(LabelFrame):
        """Select a filename and path for the new Datastore file.
        
        Attributes
        ----------
        filename : str
            The full path and filename to the database file.
        
        """
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._isReady = False
            self.filename = StringVar()
            self.filename.set('')
            
            Grid.columnconfigure(self, 1, weight = 1)
            
            self.button = Button(self, text="Browse",
                                 command=self.loadFile, width=10)
            self.button.grid(row = 0, column=1,
                             padx = 5, pady = 5, sticky = E)
            
            self.entry = Entry(self, width = 65, textvariable = self.filename)
            self.entry.delete(0, END)
            self.entry.insert(0, 'Enter a path to a new datastore file...')
            self.entry.grid(row = 0, column = 0,
                            padx = 5, pady = 5, sticky = W)
                            
            def setReady(a,b,c):
                self._isReady = True
                            
            self.filename.trace('w', setReady)
            
        @property
        def isReady(self):
            return self._isReady
    
        def loadFile(self):
            fname = asksaveasfilename(filetypes=(('HDF5 files', '*.h5'),
                                                 ('All files', '*.*')),
                                      title       = 'Select a new file...',
                                      initialfile = 'datastore.h5')
            if fname:
                self.entry.configure(state = 'normal')
                self.entry.delete(0, END)
                self.entry.insert(0, fname) # also updates self.filename
                self._isReady = True
            
    class Frame_SelectOptions(LabelFrame):
        """Selects the optional arguments for the build.
        
        Attributes
        ----------
        readTiffTags : tkinter
        
        """
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._isReady = True
            
            Grid.columnconfigure(self, 1, weight = 1)
            
            self.button = Button(self, text='Help',
                                 command=openMiscHelp, width=10)
            self.button.grid(row = 0, column=1,
                             padx = 5, pady = 5, sticky = E)        
            
                       
            
            self._kwargs = Entry(self, width = 65)
            self._kwargs.delete(0, END)
            self._kwargs.insert(0, '\'sep\' : \',\', \'readTiffTags\' : False')
            self._kwargs.grid(row = 0, column = 0,
                padx = 5, pady = 5, sticky = W)
        
        @property
        def isReady(self):
            return self._isReady
            
        @property
        def kwargs(self):
            """Parses the textbox into a Python dict.
            
            """
            return ast.literal_eval('{' + self._kwargs.get() + '}')
            
    class Frame_SelectParser(LabelFrame):
        """Selects the parser to use during the database build.
        
        Attributes
        ----------
        parser  : bstore.parsers.Parser
    
        """
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._isReady = False
            
            Grid.rowconfigure(self, 0, weight = 1)
            Grid.columnconfigure(self, 0, weight = 1)
            
            # Create a list of all available parsers and their class objects
            self._pList = [(name, parser()) for name, parser
                           in inspect.getmembers(parsers, inspect.isclass)
                           if issubclass(parser, parsers.Parser)
                              and name != 'Parser']
                              
            plugins = _utils.findPlugins('Parser')
            self._pList.extend(((name, parser()) for name, parser in plugins))
            
            # value = 1 prevents PositionParser's config window from opening
            v = IntVar(value = 1) 
            parent = self.master
            for index, (text, _) in enumerate(self._pList):
                b = Radiobutton(
                    self, text=text, variable = v, value=index,
                    command = lambda: self._configureParser(v, parent))
                b.grid(row = index, column = 0, sticky = W)
            
            # Intialize the parser contained by the LabelFrame
            self._configureParser(v, parent)
            self._isReady = True
        
        @property
        def isReady(self):
            return self._isReady
        
        def _configureParser(self, radioButtonValue, parent):
            """Determines the active parser radio button.
            
            radioButtonValue : IntVar
            parent           : tkinter.Tk object
            
            """
            # Set the parser instance and launch its GUI configuration.
            index       = radioButtonValue.get()
            self.parser = self._pList[index][1]
            
            if self.parser.requiresConfig:
                self.parser.gui(parent)
                
    class Frame_SelectSearchPath(LabelFrame):
        """Select a path to search for files to build the database with.
        
        Attributes
        ----------
        searchPath : str
        
        """
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._isReady   = False
            self.searchPath = StringVar()
            self.searchPath.set('')
            
            Grid.columnconfigure(self, 1, weight = 1)
            
            self.button = Button(self, text="Browse",
                                 command=self.loadFile, width=10)
            self.button.grid(row=0, column=1,
                             padx = 5, pady = 5, sticky = E)        
            
            self.entry = Entry(self, width = 65,
                               textvariable = self.searchPath)
            self.entry.delete(0, END)
            self.entry.insert(
                0, 'Enter the directory containing the input files...')
            self.entry.grid(row = 0, column = 0,
                            padx = 5, pady = 5, sticky = W)
                            
            def setReady(a,b,c):
                self._isReady = True
                            
            self.searchPath.trace('w', setReady)
            
        @property
        def isReady(self):
            return self._isReady
    
        def loadFile(self):
            fname = askdirectory(title = 'Select a search directory...',
                                 mustexist = True)
            if fname:
                self.entry.configure(state = 'normal')
                self.entry.delete(0, END)
                self.entry.insert(0, fname) # also updates self.searchPath
                self._isReady = True