import pandas as pd
from pathlib import Path
import DataSTORM.processors as dsproc
import trackpy as tp

class BatchProcessor:
    """Base class for processing and saving single-molecule microscopy data.
    
    Attributes
    ----------
    fileList : list of Path
        List of Path objects pointing to all the identified localization files
        in a directory or a directory tree.    
    pipeLine : list of Processors
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
            self.fileList = self._parseDirectory(str(inputDirectory), suffix)
            self.pipeline = pipeline
            
            if  not self.pipeline:
                raise UserWarning
            elif not self.fileList:
                raise ValueError('Error: No files ending in {:s} were found.'.format(suffix))
        except UserWarning:
            print('Warning: Pipeline contains no Processors.')
        
        self._useSameFolder   = useSameFolder
        self._outputDirectory = Path(outputDirectory)
        self._suffix          = suffix
        self._delimiter       = delimiter
        
        # Remember the paths to all the processed files here
        self._outputFileList   = []
        
        if (not self._outputDirectory.exists()) and (not self._useSameFolder):
            print('Output directory does not exist. Creating it...')
            self._outputDirectory.mkdir()
            print('Created folder {:s}'.format(str(self._outputDirectory.resolve())))
            
    def go(self):
        """Initiate batch processing on all the files.
        
        """
        # Perform batch processing on all files
        for file in self.fileList:
            inputFile = str(file.resolve())
            
            # In future versions, allow user to set the import command
            df   = pd.read_csv(inputFile, sep = self._delimiter)
            
            # Run each processor on the DataFrame
            for proc in self.pipeline:
                df = proc(df)
            
            # Save the final DataFrame
            if self._useSameFolder:
                fileStem = file.resolve().parent / file.stem
            else:
                fileStem = self._outputDirectory / file.stem
                
            outputFile = str(fileStem) + '_processed' + '.dat'
            self._outputFileList.append(Path(outputFile))
            
            # In future versions, allow user to set the export command
            df.to_csv(outputFile, sep = self._delimiter, index = False)
            
            
    def _parseDirectory(self, inputDirectory, suffix = '.dat'):
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
        
class H5BatchProcessor(BatchProcessor):
    """Performs batch processing from CSV or H5 to H5 datafiles.
    
    Notes
    -----
    Due to the nature of out-of-core processing, only CleanUp and Filter
    processors are supported via this class.
    
    """
    def __init__(self,
                 inputDirectory,
                 pipeline,
                 useSameFolder   = False,
                 outputDirectory = 'processed_data',
                 suffix          = '.h5',
                 delimiter       = ',',
                 inputFileType   = 'csv',
                 inputKey        = 'raw',
                 chunksize       = 2e6):
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
        inputFileType   : str         (default: 'csv')
            Specifies the input file type and determines which Pandas import
            command is used. Can be either 'csv' or 'hdf'.
        inputKey        : str         (default: 'raw')
            The key to the DataFrame inside the h5 file that will be processed.
            This is only used if h5 files are being processed in batch.
        chunksize       : float       (default: 2e6)
            The number of rows to read when performing out-of-core processing.
        
        """
        super(H5BatchProcessor, self).__init__(inputDirectory,
                                               pipeline,
                                               useSameFolder,
                                               outputDirectory,
                                               suffix,
                                               delimiter)
        
        if (inputFileType != 'csv') and (inputFileType != 'hdf'):
            message = "Error: Input file type must be either 'csv' or 'hdf'"
            print(message)
            raise ValueError(message)
        
        self._inputFileType = inputFileType                                       
        self._inputKey      = inputKey
        self._chunksize     = chunksize

    def go(self):
        """Initiate batch processing on all the files.
        
        """
        # Perform batch processing on all files
        for file in self.fileList:
            inputFile = str(file.resolve())

            # Determines the output file and opens the store for streaming
            if self._useSameFolder:
                fileStem = file.resolve().parent / file.stem
            else:
                fileStem = self._outputDirectory / file.stem
                
            outputFile  = str(fileStem) + '_processed.h5'
            outputStore = pd.HDFStore(outputFile)
            
            # Read the data and divide it into chunks
            if self._inputFileType == "hdf":
                inputData = pd.read_hdf(inputFile,
                                        key = self._key,
                                        chunksize = self._chunksize)
            else:
                inputData = pd.read_csv(inputFile,
                                        sep = self._delimiter,
                                        chunksize = self._chunksize)
                                        
            # Convert to a format without units. This is to make the columns in
            # the hdf file searchable.
                converter  = dsproc.ConvertHeader(dsproc.FormatThunderSTORM(),
                                                  dsproc.FormatLEB())
                modPipeline = [converter] + self.pipeline
                
            
            # Iterate over each chunk                               
            for ctr, chunk in enumerate(inputData):
                
                # Run each processor on the data in the store
                for proc in modPipeline:
                    df = proc(chunk)
            
                # Write the chunk to the hdf file
                outputStore.append('raw',
                                   df,
                                   format = 'table',
                                   data_columns = True)
            
            outputStore.close()
            self._outputFileList.append(Path(outputFile))
            
    def goMerge(self, mergeRadius = 40, tOff = 1, preprocessed = True):
        """Performs out-of-core merging on HDF files.
        
        goMerge requires HDF files (.h5) as inputs because the columns may be
        queried directly from disk. Merged data is written directly into the
        same h5 file, but with a different key.
        
        Parameters
        ----------
        preprocessed : bool (default: False)
            Was the data already preprocssed in batch? If True, use the
            self._outputFileList from the previous go() operation as inputs for
            merging. Otherwise, use the files from the search of
            inputDirectory.
        """
        if preprocessed:        
            fileList = self._outputFileList
        else:
            fileList = self.fileList
            
        for file in fileList:
            inputFile = str(file.resolve())
            
            # Link nearby localizations into one
            with tp.PandasHDFStoreSingleNode(inputFile, key = self._inputKey) as s:
                for linked in tp.link_df_iter(s, mergeRadius, memory = tOff):
                    s.store.append('linked', linked, data_columns = True)           

if __name__ == '__main__':
    from pathlib import Path
    import processors
    
    p               = Path('../test-data/')
    outputDirectory = Path('../processed_data')
    proc1           = processors.ConvertHeader(FormatThunderSTORM(), FormatLEB())
    proc2           = processors.Cluster(minSamples = 50, eps = 20, coordCols = ['x','y'])
    pipeline        = [proc1]
    
    bp = BatchProcessor(p, pipeline, outputDirectory = outputDirectory)
    bp.go()