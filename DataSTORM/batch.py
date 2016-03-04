import pandas as pd
from pathlib import Path
import DataSTORM.processors as dsproc
import trackpy as tp
import numpy as np
import h5py
import matplotlib.pyplot as plt

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
                 inputFormat     = 'csv',
                 useSameFolder   = False,
                 outputDirectory = 'processed_data',
                 searchString    = '.dat',
                 delimiter       = ',',
                 saveFormat      = 'csv',
                 h5SaveName      = 'DataSTORM',
                 h5SaveKey       = 'processed_localizations'):
        """Parse the input directory by finding SMLM data files.
        
        The constructor parses the input directory and creates a list of Path
        objects all pointing to data files.
        
        Parameters
        ----------
        inputDirectory  : str or Path
            A string to a directory or hdf file containg SMLM data files, or a
            pathlib Path instance to a directory or hdf file.
        pipeline        : list of Processors
            List of Processor objects to process the data.
        inputFormat     : str         (default: 'csv')
            One of 'csv' or 'hdf'.
        useSameFolder   : bool        (default: False)
            Place output results in the same folder as the inputs?
        outputDirectory : str or Path (default: 'processed_data')
            Relative path to the folder for saving the processed results. This
            is ignored if useSameFolder is True.
        searchString    : str         (default: '.dat')
            The string identifying SMLM data files.
        delimiter       : str         (default: ',')
            Delimiter used to separate entries in csv data files.
        saveFormat      : str         (default: 'csv')
            One of 'csv' or 'hdf'.
        h5SaveName      : str         (default: 'DataSTORM')
            The filename of the output hdf5 store. This is ignored if
            saveFormat is set to 'csv' OR useSameFolder is True.
        h5SaveKey       : str         (default: 'processed_localizations')
            The stem (last part) of the key that identifies the dataset.
        
        """
        if inputFormat == 'csv':
            searchHDF = False
        elif inputFormat == 'hdf':
            searchHDF = True
        else:
            raise ValueError('Error: inputFormat must be \'csv\' or \'hdf\'. \'{:s}\' was provided.'.format(saveFormat))
        
        try:        
            self.fileList = self._parseDirectory(str(inputDirectory), searchString, searchHDF)
            self.pipeline = pipeline
            
            if  not self.pipeline:
                raise UserWarning
            elif not self.fileList:
                raise ValueError('Error: No files ending in {:s} were found.'.format(searchString))
            elif saveFormat not in ['csv', 'hdf']:
                raise ValueError('Error: saveFormat must be \'csv\' or \'hdf\'. \'{:s}\' was provided.'.format(saveFormat))
        except UserWarning:
            print('Warning: Pipeline contains no Processors.')
        
        self._inputDirectory  = inputDirectory
        self._inputFormat     = inputFormat
        self._useSameFolder   = useSameFolder
        self._outputDirectory = Path(outputDirectory)
        self._searchString    = searchString
        self._delimiter       = delimiter
        self._saveFormat      = saveFormat
        self._h5SaveName      = h5SaveName + '.h5'
        self._h5SaveKey       = h5SaveKey
        
        # Remember the paths to all the processed files here
        self._outputFileList   = []
        
        if (not self._outputDirectory.exists()) and (not self._useSameFolder):
            print('Output directory does not exist. Creating it...')
            self._outputDirectory.mkdir()
            print('Created folder {:s}'.format(str(self._outputDirectory.resolve())))
            
    def go(self):
        """Initiate batch processing on all the files.

        """
        # Perform batch processing on all files.
        # It's important to note that 'file' is a csv file if the inputFormat
        # is 'csv'. If inputformat is 'hdf', it's the group directory pointing
        # to a dataset, not the hdf file itself.
        for file in self.fileList:
            print('Processing file {:s}'.format(str(file)))            
            
            # Load the DataFrame
            if   self._inputFormat == 'csv':
                inputFile = str(file.resolve())
                df        = pd.read_csv(inputFile, sep = self._delimiter)
            elif self._inputFormat == 'hdf':
                inputKey = str(file)
                df   = pd.read_hdf(str(self._inputDirectory), key = inputKey)

            # Run each processor on the DataFrame
            for proc in self.pipeline:
                df = proc(df)
            
            # Save the final DataFrame to a csv flat file
            if self._saveFormat == 'csv':
                # Set the csv filename stem
                if self._useSameFolder:
                    fileStem = file.resolve().parent / file.stem
                else:
                    fileStem = self._outputDirectory / file.stem                
                
                # Write the data
                outputFile = str(fileStem) + '_processed' + '.dat'                
                df.to_csv(outputFile, sep = self._delimiter, index = False)
               
            # Save the final DataFrame to a hdf5 store
            elif self._saveFormat == 'hdf':
                if self._useSameFolder:
                    outputFile = self._inputDirectory
                else:
                    outputFile = self._outputDirectory / Path(self._h5SaveName)
                
                outputStore = pd.HDFStore(str(outputFile))
                
                # Write the final DataFrame to the hdf file
                if self._inputFormat == 'csv':
                    keyStem = self._genKey(file.stem)
                    
                    # Convert to a format without units. This is to make the
                    # columns in the hdf file searchable.
                    converter  = dsproc.ConvertHeader(dsproc.FormatThunderSTORM(),
                                                      dsproc.FormatLEB())
                    df = converter(df)                    
                elif self._inputFormat == 'hdf':
                    keyStem = str(file.parent)
                    
                outputStore.put(keyStem + '/' + self._h5SaveKey,
                                df,
                                format       = 'table',
                                data_columns = True,
                                index        = False)
            
                outputStore.close()
            
            # Remember the output files                
            self._outputFileList.append(Path(outputFile))
            
    def _parseDirectory(self,
                        inputDirectory,
                        searchString = '.dat',
                        searchHDF    = False,):
        """Finds all localization data files in a directory tree or HDF file.
        
        Parameters
        ----------
        inputDirectory : str
            String of the directory tree containing SMLM data files.
        searchString   : str  (optional, default: '.dat')
            Ending suffix for csv localization result files or keys to
            localization results in an hdf file. This must be unique to
            files containing localization data.
        searchHDF      : bool (optional, default: False)
            If True, searches a HDF file for localization files matching
            searchString.
        
        Returns
        -------
        locResultFiles : list of Path
            A list of all the localization data files in a directory tree/
            HDF file.
        """
        if not searchHDF:
            inputDirectory    = Path(inputDirectory)
            locResultFilesGen = inputDirectory.glob('**/*{:s}'.format(searchString))
            locResultFiles    = sorted(locResultFilesGen)
        
            return locResultFiles
        else:
            # Open the hdf file
            f = h5py.File(inputDirectory, 'r')
            
            # Extract all localization filesets from the HDF5 file by matching
            # each group to the search string.
            # ('table' not in name) excludes the subgroup inside every
            # processed_localization parent group.
            locResultFiles = []
            def find_locs(name):
                """Finds localization files matching the name pattern."""
                if (searchString in name) and ('table' not in name):
                    locResultFiles.append(name)
            f.visit(find_locs)
            f.close()
            
            return list(map(Path, locResultFiles))
        
    def _genKey(self, fileStem, sep = '_MMStack'):
        """Generates a key string from csv files for a dataset in a h5 file.
        
        """
        # Removes everything after and including sep, usually '_MMStack...'
        subkey, _ = fileStem.split(sep = sep)
        
        # Removes the number to create the parent key
        # For example, HeLaS_shTRF_1 becomes HeLaS_shTRF
        parentKey = subkey.split(sep = '_')
        parentKey.pop()
        parentKey = '_'.join(parentKey)
        
        return parentKey + '/' + subkey
    
    @staticmethod
    def bindImage(h5Filename, searchFolder):
        """Finds widefield images and saves them to an hdf5 file.
        
        bindImage() searches a directory for widefield images that match the
        keys in an hdf5 file and saves these images to the file.
        
        """
        # Open the h5 file and read its keys
        f = h5py.File(str(h5Filename), 'a')        
        
        # Loop through each dataset's subkeys and find a matching WF file
        # fov = field of view
        for dataset in f.keys():
            for fov in f[dataset].keys():
                # Get the current fov number
                fovNum = fov.split(sep = '_'); fovNum = fovNum[-1]
                
                # Search the folder for the widefield images
                searchString = '**/' + dataset + '*_WF' + str(fovNum) + '*'
                folder = searchFolder.glob(searchString)
                folder = sorted(folder)
                
                # There should be only one widefield image
                assert len(folder) == 1, \
                       'Error: multiple widefield image directories found. Are they named correctly?'

                image = folder[0].glob('**/*.tif')
                image = sorted(image)
                assert len(image) == 1, \
                       'Error: multiple widefield images found. Are there multiple images in a directory?'
                image = image[0]
                
                # Read the image into memory, then save it to the hdf5 file
                wfImage = plt.imread(str(image))
                saveKey = dataset + '/' + fov + '/widefield_image'
                saveImg = f.create_dataset(saveKey,
                                           wfImage.shape,
                                           data = wfImage) 
                
                print('Binding {0:s} to {1:s}...'.format(str(image), saveKey))
                
        f.close()
        
class H5BatchProcessor(BatchProcessor):
    """Performs batch processing from CSV or H5 to H5 datafiles. This class is
    ONLY used for out-of-core processing.
    
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
                 searchString    = '.h5',
                 delimiter       = ',',
                 inputFileType   = 'csv',
                 inputKey        = 'raw',
                 outputKey       = 'processed',
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
        searchString    : str         (default: '.dat')
            The string identifying SMLM data files.
        delimiter       : str         (default: ',')
            Delimiter used to separate entries in the data files.
        inputFileType   : str         (default: 'csv')
            Specifies the input file type and determines which Pandas import
            command is used. Can be either 'csv' or 'h5'.
        inputKey        : str         (default: 'processed')
            The key to the DataFrame inside the h5 file that will be processed.
            This is only used if h5 files are being processed in batch.
        outputKey       : str         (default: 'processed')
            The key to the DataFrame for writing.
        chunksize       : float       (default: 2e6)
            The number of rows to read when performing out-of-core processing.
            Set this to None if you don't want chunking to occur.
        
        """
        super(H5BatchProcessor, self).__init__(inputDirectory,
                                               pipeline,
                                               useSameFolder,
                                               outputDirectory,
                                               searchString,
                                               delimiter)
        
        if (inputFileType != 'csv') and (inputFileType != 'h5'):
            message = "Error: Input file type must be either 'csv' or 'h5'"
            print(message)
            raise ValueError(message)
        
        self._inputFileType = inputFileType                                       
        self._inputKey      = inputKey
        self._outputKey     = outputKey
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
            if self._inputFileType == "h5":
                inputData = pd.read_hdf(inputFile,
                                        key = self._inputKey,
                                        chunksize = self._chunksize,
                                        iterator  = True)
            else:
                inputData = pd.read_csv(inputFile,
                                        sep = self._delimiter,
                                        chunksize = self._chunksize,
                                        iterator  = True)
                                        
            # Convert to a format without units. This is to make the columns in
            # the hdf file searchable.
                converter  = dsproc.ConvertHeader(dsproc.FormatThunderSTORM(),
                                                  dsproc.FormatLEB())
                modPipeline = [converter] + self.pipeline
                
            
            # Iterate over each chunk                               
            for chunk in inputData:
                
                # Run each processor on the data in the store
                for proc in modPipeline:
                    df = proc(chunk)
            
                # Write the chunk to the hdf file
                outputStore.append(self._outputKey,
                                   df,
                                   format = 'table',
                                   data_columns = True)
            
            outputStore.close()
            self._outputFileList.append(Path(outputFile))
            
    def goMerge(self,
                mergeRadius = 40,
                tOff         = 1,
                preprocessed = True,
                writeChunks  = 10000):
        """Performs both out-of-core and in-core merging on HDF files.
        
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
        chunkSize    : int  (default: 10000)
            The number of trajectories to save at once to the HDF file. Larger
            numbers give better performance but consume more memory.
        """
        # Create a Merge instance for computing statistics
        merger = dsproc.Merge(autoFindMergeRadius = False,
                              mergeRadius = mergeRadius,
                              tOff = tOff)        
        
        if preprocessed:        
            fileList = self._outputFileList
        else:
            fileList = self.fileList
            
        for file in fileList:
            inputFile = str(file.resolve())
            
            # Link nearby localizations into one
            with tp.PandasHDFStoreSingleNode(inputFile, key = self._outputKey) as s:
                for linked in tp.link_df_iter(s, mergeRadius, memory = tOff):
                    # Stream linked dataset to a temporary table named 'linked'
                    # inside the same hdf file.
                    s.store.append('linked', linked, data_columns = True)
                    
            # Compute the statistics for each trajectory
            with tp.PandasHDFStoreSingleNode(inputFile, key = 'linked') as s:
                maxParticle = s.store.select_column('linked', 'particle').max()
                maxParticle = int(maxParticle)
                
                # Chunk trajectories for faster processing
                # (~10000 trajectory chunks)
                chunkSize = int(maxParticle / writeChunks) + 1
                particleChunks = np.array_split(np.arange(maxParticle),
                                                chunkSize)
                
                # Loop over each trajectory (trackpy calls them particles)
                for chunk in particleChunks:
                    minTraj = np.min(chunk)
                    maxTraj = np.max(chunk)
                                        
                    # Select all particles in the current chunk
                    select  = ['particle>={:d}'.format(minTraj),
                               'particle<={:d}'.format(maxTraj)]
                    locData = s.store.select('linked', where = select).groupby('particle')
                    
                    # Send particle to Merge object to compute its statistics
                    procdf = merger.calcGroupStats(locData)
                    
                    #Save this trajectory to the store in the 'merged' table
                    s.store.append('merged', procdf, data_columns = True)
            
                # Remove the linked table from the hdf5 file
                s.store.remove('linked')
        

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