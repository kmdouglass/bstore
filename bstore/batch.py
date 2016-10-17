# © All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Switzerland, Laboratory of Experimental Biophysics, 2016
# See the LICENSE.txt file for more details.

import bstore.config
__version__ = bstore.config.__bstore_Version__

import pandas as pd
from pathlib import Path
from abc import ABCMeta, abstractmethod, abstractproperty
import bstore.database as dsdb
import json

class BatchProcessor(metaclass = ABCMeta):
    """Batch processor metaclass. All batch processors must inherit this.
    
    """
    @abstractproperty
    def datasetList(self):
        pass
    
    @abstractmethod
    def go(self):
        pass

class CSVBatchProcessor(BatchProcessor):
    """Batch processing and saving for SMLM data in CSV files.
    
    Attributes
    ----------
    datasetList : list of Path
        List of Path objects pointing to all the identified localization files
        in a directory or a directory tree.    
    pipeLine    : list of Processors
        List of Processor objects to process the data.
    """
    
    def __init__(self,
                 inputDirectory,
                 pipeline,
                 useSameFolder   = False,
                 outputDirectory = 'processed_data',
                 suffix          = '.dat',
                 delimiter       = ','):
        """Parse the input directory by finding SMLM data files.
        
        The constructor parses the input directory and creates a list of Path
        objects all pointing to data files.
        
        Parameters
        ----------
        inputDirectory  : str or Path
            A string to a directory containg SMLM data files, or a pathlib Path
            instance to a directory.
        pipeline        : list of Processors
            List of Processor objects to process the data.
        useSameFolder   : bool        (default: False)
            Place output results in the same folder as the inputs?
        outputDirectory : str or Path (default: 'processed_data')
            Relative path to the folder for saving the processed results. This
            is ignored if useSameFolder is True.
        suffix          : str         (default: '.dat')
            The suffix identifying SMLM data files.
        delimiter       : str         (default: ',')
            Delimiter used to separate entries in the data files.
        
        """
        try:        
            self.datasetList = self._parseDatasets(str(inputDirectory), suffix)
            self.pipeline = pipeline
            
            if  not self.pipeline:
                raise UserWarning
            elif not self.datasetList:
                raise ValueError(
                   'Error: No files ending in {:s} were found.'.format(suffix))
        except UserWarning:
            print('Warning: Pipeline contains no Processors.')
        
        self._useSameFolder   = useSameFolder
        self._outputDirectory = Path(outputDirectory)
        self._suffix          = suffix
        self._delimiter       = delimiter
            
    def go(self, processedFlag = 'processed'):
        """Initiate batch processing on all the files.
        
        Parameters
        ----------
        processedFlag : str
            The string to append to the input filenames for naming output
            files. Files will have the same name as the inputs with this
            string appended to the end. For example, an input of
            "Cells_Results.dat" will produce an output named
            "Cells_Results_processed.dat".
        
        """
        if (not self._outputDirectory.exists()) and (not self._useSameFolder):
            print('Output directory does not exist. Creating it...')
            self._outputDirectory.mkdir()
            print('Created folder {:s}'.format(
                                         str(self._outputDirectory.resolve())))
        
        # Perform batch processing on all files
        for file in self.datasetList:
            inputFile = str(file.resolve())
            
            df   = pd.read_csv(inputFile, sep = self._delimiter)
            
            # Run each processor on the DataFrame
            for proc in self.pipeline:
                df = proc(df)
            
            # Save the final DataFrame
            if self._useSameFolder:
                fileStem = file.resolve().parent / file.stem
            else:
                fileStem = self._outputDirectory / file.stem
                
            outputFile = str(fileStem) + '_' + processedFlag + '.csv'
            
            # Output the results to a file.
            # This will overwrite any existing files (mode = 'w').
            df.to_csv(outputFile,
                      sep   = self._delimiter,
                      mode  = 'w',
                      index = False)
    
    @property        
    def datasetList(self):
        """A list of all pathlib Path objects to the datasets to process.
        
        """
        return self._datasetList
        
    @datasetList.setter
    def datasetList(self, paths):
        """
        Parameters
        ----------
        paths : list of Path
            Paths to all the datasets to be processed.
        
        """
        self._datasetList = paths
            
    def _parseDatasets(self, inputDirectory, suffix = '.dat'):
        """Finds all localization data files in a directory or directory tree.
        
        Parameters
        ----------
        inputDirectory : str
            String of the directory tree containing SMLM data files.
        suffix         : str (optional, default: '.dat')
            Suffix for localization result files. This must be unique to
            files containing localization data.
        
        Returns
        -------
        locResultFiles : list of Path
            A list of all the localization data files in a directory tree.
        """
        inputDirectory    = Path(inputDirectory)
        locResultFilesGen = inputDirectory.glob('**/*{:s}'.format(suffix))
        locResultFiles    = sorted(locResultFilesGen)
        
        return locResultFiles
        
class HDFBatchProcessor(BatchProcessor):
    """Automatic processing of localizations stored in a HDF datastore.
    
    """
    def __init__(self,
                 inputDatastore,
                 pipeline,
                 outputDirectory = 'processed_data',
                 searchString    = 'Localizations'):
        """Parse the input datastore by finding SMLM data files.
        
        The constructor parses the HDF datastore and creates a list of Path
        objects all pointing to localization datasets.
        
        Parameters
        ----------
        inputDatastore  : str or Path
            A string or Path to an HDF datastore.
        pipeline        : list of Processors
            List of Processor objects to process the data.
        outputDirectory : str or Path
            Relative path to the folder for saving the processed results.
        searchString    : str
            The dataset type to process in batch.
        
        """
        # TODO: Check for file's existence
        self._db = dsdb.HDFDatastore(inputDatastore)
        try:        
            self.datasetList = self._db.query(searchString)
            self.pipeline = pipeline
            
            if  not self.pipeline:
                raise UserWarning
            elif not self.datasetList:
                raise ValueError(
                   'Error: No datasets containing {:s} were found.'.format(searchString))
        except UserWarning:
            print('Warning: Pipeline contains no Processors.')
        
        self._outputDirectory = Path(outputDirectory)
        self._searchString    = searchString
        
    def _genFileName(self, dsID):
        """Generate an output file name for a processed dataset.
        
        Parameters
        ----------
        dsID     : Dataset
        
        Returns
        -------
        fileName : Path
        
        """
        acqKey    = '/'.join([dsID.prefix, dsID.prefix]) + \
                    '_' + str(dsID.acqID)
                                 
        otherIDs = ''
        if dsID.channelID is not None:
            otherIDs += '_Channel' + dsID.channelID
        if dsID.posID is not None:
            if len(dsID.posID) == 1:
                posID = dsID.posID[0]    
                otherIDs += '_Pos{:d}'.format(posID)
            else:
                otherIDs += '_Pos_{0:0>3d}_{1:0>3d}'.format(dsID.posID[0], 
                                                            dsID.posID[1])
        if dsID.sliceID is not None:
            otherIDs += '_Slice{:d}'.format(dsID.sliceID)
        
        fileName = acqKey + '/' + dsID.datasetType + otherIDs
            
        return Path(fileName)
    
    def _writeAtomicIDs(self, filename, dsID):
        """Writes the atomic ID information to a text file.
        
        Parameters
        ----------
        filename : str
        dsID     : datasetID
        """
        
        with open(filename, 'w') as outfile:
            json.dump(dsID, outfile)
    
    @property
    def datasetList(self):
        """A list of all datasets to process.
        
        """
        return self._datasetList
    
    @datasetList.setter
    def datasetList(self, paths):
        self._datasetList = paths
    
    def go(self):
        if (not self._outputDirectory.exists()):
            print('Output directory does not exist. Creating it...')
            self._outputDirectory.mkdir()
            print('Created folder {:s}'.format(
                                         str(self._outputDirectory.resolve())))
        else:
            raise ProcessedFolderExists(('Error: the output directory already '
                'exists. Please remove it or choose a new directory.'))
                                         
        # Perform batch processing on all datasets
        for currDataset in self.datasetList:
            
            atom = self._db.get(currDataset)
            df = atom.data
            
            # Run each processor on the DataFrame
            for proc in self.pipeline:
                df = proc(df)
            
            # Build the directory structure
            outputFile = self._outputDirectory / self._genFileName(currDataset)
            if not outputFile.parent.parent.exists():
                outputFile.parent.parent.mkdir()
            if not outputFile.parent.exists():
                outputFile.parent.mkdir()
            
            outputFileString = str(outputFile) + '.csv'
            
            # Output the results to a file.
            # This will overwrite any existing files (mode = 'w').
            df.to_csv(outputFileString,
                      sep   = ',',
                      mode  = 'w',
                      index = False)
                      
            # Write the datastore atomic IDs to the same folder
            idFilename = str(outputFile) + '.json'
            self._writeAtomicIDs(idFilename, currDataset)
                      
class ProcessedFolderExists(Exception):
    """Attempting to write processed output to an existing folder.
    
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)