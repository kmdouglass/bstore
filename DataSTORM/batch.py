import pandas as pd
from pathlib import Path
from abc import ABCMeta, abstractmethod, abstractproperty
import DataSTORM.processors as dsproc
import trackpy as tp
import numpy as np
import h5py
import matplotlib.pyplot as plt

class BatchProcessor(metaclass = ABCMeta):
    """Batch processor metaclass. All batch processors must inherit this.
    
    """
    @abstractproperty
    def datasetList(self):
        pass
    
    @abstractmethod
    def go(self):
        pass
    
    @abstractmethod
    def _parseDatasets(self):
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
                
            outputFile = str(fileStem) + '_' + processedFlag + '.dat'
            
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
    """Automatic processing of localizations stored in a HDF database.
    
    """
    def __init__(self,
                 inputDatabase,
                 pipeline,
                 outputDirectory = 'processed_data',
                 searchString    = 'locResults',
                 delimiter       = ','):
        """Parse the input database by finding SMLM data files.
        
        The constructor parses the HDF database and creates a list of Path
        objects all pointing to localization datasets.
        
        Parameters
        ----------
        inputDirectory  : str or Path
            A string to a directory containg SMLM data files, or a pathlib Path
            instance to a directory.
        pipeline        : list of Processors
            List of Processor objects to process the data.
        outputDirectory : str or Path (default: 'processed_data')
            Relative path to the folder for saving the processed results.
        searchString    : str         (default: 'locResults')
            The suffix identifying SMLM data files.
        delimiter       : str         (default: ',')
            Delimiter used to separate entries in the data files.
        
        """
        try:        
            self.datasetList = self._parseDatasets(str(inputDatabase), searchString)
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
        self._delimiter       = delimiter
    
    @property
    def datasetList(self):
        """A list of all pathlib Path objects to the datasets to process.
        
        """
        return self._datasetList
    
    @datasetList.setter
    def datasetList(self, paths):
        self._datasetList = paths
    
    def go(self):
        pass
    
    def _parseDatasets(self, inputDirectory, searchString = 'locResults'):
        """Finds all localization datasets in an HDF database.
        
        Parameters
        ----------
        inputDirectory : str
            String of the directory tree containing SMLM data files.
        searchString   : str  (optional, default: '.dat')
            Strings identifying localization results. This must be unique to
            keys containing localization data.
        
        Returns
        -------
        locResults : list of Path
            A list of all the localization datasets in the HDF file.
            
        """
        pass
        #TODO: Reformulate the input parameters