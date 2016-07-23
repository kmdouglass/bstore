.. -*- mode: rst -*-
   
***********
Quick Start
***********

:Author: Kyle M. Douglass
:Contact: kyle.m.douglass@gmail.com
:organization: École Polytechnique Fédérale de Lausanne (EPFL)
:revision: $Revision: 0 $
:date: 2016-07-23

:abstract:

   This quick start guide shows how to get up and running with B-Store
   as quickly as possible.
   
.. meta::
   :keywords: quickstart
   :description lang=en: Quick Start guide for B-Store.
	      
.. contents:: Table of Contents

Installation
============

Installation is most easily performed using the Anaconda package
manager::

  conda update conda
  conda install -c kmdouglass -c soft-matter bstore

Alternatively, the source code for B-Store may be cloned from
https://github.com/kmdouglass/bstore/. A list of dependencies may be
found inside the *requirements.txt* file inside the repository.
      
Workflow Summary
================

The B-Store workflow is divided between these two tasks: 

1. Sort and place all the files from a single molecule localization
   microscopy (SMLM) acquisition into a database.
2. Automatically access this database for batch analyses.

B-Store uses popular scientific Python libraries for working with SMLM
data. Most notably, it uses `Pandas DataFrames`_ for working with
tabulated localization data and the standard `json module`_ for
handling metadata. Images are treated as `NumPy arrays`_. If you can't
do something with B-Store, chances are you can implement a custom
solution using another Python library.

.. _Pandas DataFrames: http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html
.. _json module: https://docs.python.org/3/library/json.html
.. _NumPy arrays: http://docs.scipy.org/doc/numpy/reference/generated/numpy.array.html

We are currently exploring ways to enable B-Store to handle OME.TIFF
metadata and drift correction data as well.

Jupyter Notebook Examples
=========================

If you find that this quickstart guide insufficient, you can find more
examples inside the Jupyter Notebooks at the `B-Store GitHub
repository`_.

.. _B-Store GitHub repository: https://github.com/kmdouglass/bstore/tree/master/examples

Working with B-Store
====================

B-Store is a collection of classes and functions for working with SMLM
data. You interact with these classes and functions by writing Python
code.

`Jupyter Notebooks`_ are a great way to interactively work with
B-Store and are very common in the scientific Python community. They
are free, powerful, and provide a convenient way to document your work
and share it with others. Alternatively, you may use any other Python
interpreter to work with B-Store.

.. _Jupyter Notebooks: http://jupyter.org/

B-Store Test Datasets
+++++++++++++++++++++

The `B-Store test files repository`_ contains a number of datasets for
B-Store's unit tests. These datasets may also be used to try out the
code in the `examples`_ or in this guide.

.. _B-Store test files repository: https://github.com/kmdouglass/bstore_test_files
.. _examples: https://github.com/kmdouglass/bstore/tree/master/examples

Parsing Datasets to Assign Database IDs
+++++++++++++++++++++++++++++++++++++++

A B-Store database is a storage container for things like sets of
localizations, widefield images, and acquisition metadata. Each
dataset in the database is given a unique ID by a parser. A parser
reads your data and gives it a meaningful set of database IDs. For
example, if you have localizations stored in a file named
*HeLa_Cells_1.csv* and you use the built-in `SimpleParser`_, then your
dataset will have the following ID's:

1. *prefix* - 'HeLa_Cells'
2. *acqID* - 1
3. *datasetType* - 'locResults'

::
   >>> import bstore.parsers as parsers
   >>> sp = parsers.SimpleParser()
   >>> sp.parseFilename('HeLa_Cells_1.csv')
   >>> sp.getBasicInfo()
   {'sliceID': None, 'channelID': None, 'acqID': 1, 'dateID': None, 'posID': None, 'datasetType': 'locResu
   lts', 'prefix': 'HeLa_Cells'}                                                                         

The other IDs (sliceID, channelID, posID, and dateID) are not
specified by the SimpleParser and are therefore set to None.

B-Store comes with two built-in parsers: `SimpleParser`_ and
`MMParser`_. The SimpleParser can read files that follow the format
**prefix_acqID.datasetType**. *.csv* files contain tabulated
localization data, *.tif* files contain widefield images, and *.txt*
files contain metadata in JSON format. The MMParser is more
complicated; it can assign a channelID and posID by reading a file's
filename.

If you require a customized parser to assign ID's, the Jupyter
Notebook `tutorial`_ on writing custom parsers is a good place to
look.

.. _SimpleParser: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.parsers.SimpleParser
.. _MMParser: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.parsers.MMParser
.. _tutorial: https://github.com/kmdouglass/bstore/blob/master/examples/Tutorial%203%20-%20Writing%20custom%20parsers.ipynb

Building a Database
+++++++++++++++++++

You will typically not need to work directly with a parser. Instead,
the B-Store database will use a specified parser to automatically read
your files, assign the proper ID's, and then insert the data into the
database.

Let's say you have data from an experiment that can be parsed using
the **MMParser**. (Test data for this example may be found at
https://github.com/kmdouglass/bstore_test_files/tree/master/test_experiment_2
.) First, we setup the parser and choose the directory containing
files and subdirectories of acquisition data.::

   >>> from bstore import database, parsers
   >>> from pathlib import Path
   >>> dataDirectory = Path('bstore_test_files/test_experiment_2')
   >>> parser = parsers.MMParser()

Next, we create a `HDFDatabase`_ instance. This class is used to
interact with and create B-Store databases.::

   >>> dbName = 'myFirstDatabase.h5'
   >>> myDB   = database.HDFDatabase(dbName)

Finally, we create the database by sending the parser, the parent
directory of the acqusition files, and an optional string telling the
parser how to find localization files to the **build** method of
myDB.::

   >>> myDB.build(parser, dataDirectory,
   ...            locResultsString = 'locResults_processed.csv')
   16 files were successfully parsed.
                              channelID     datasetType dateID posID sliceID
   prefix               acqID                                               
   HeLaS_Control_IFFISH 1          A647      locResults   None  (0,)    None
                        1          A647     locMetadata   None  (0,)    None
                        1          A647  widefieldImage   None  (0,)    None
                        1          A750  widefieldImage   None  (0,)    None
                        2          A647      locResults   None  (0,)    None
                        2          A647     locMetadata   None  (0,)    None
                        2          A647  widefieldImage   None  (0,)    None
                        2          A750  widefieldImage   None  (0,)    None
   HeLaS_shTRF2_IFFISH  1          A647      locResults   None  (0,)    None
                        1          A647     locMetadata   None  (0,)    None
                        1          A647  widefieldImage   None  (0,)    None
                        1          A750  widefieldImage   None  (0,)    None
                        2          A647      locResults   None  (0,)    None
                        2          A647     locMetadata   None  (0,)    None
                        2          A647  widefieldImage   None  (0,)    None
                        2          A750  widefieldImage   None  (0,)    None

This creates a file named myFirstDatabase.h5 that contains the 16
datasets listed above. (If you want to investigate the contents of the
HDF file, we recommend the `HDFView utility`_.)

.. _HDFDatabase: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.database.HDFDatabase
.. _HDFView utility: https://www.hdfgroup.org/HDF5/Tutor/hdfview.html

Batch Analysis from a B-Store Database
++++++++++++++++++++++++++++++++++++++

The real utility of the B-Store database is that it enables batch
analyses of experiments containing a large number of acquisitions
containing related but different files.

As an example, let's say you want to extract all the localization
files inside the database we just created and filter out localizations
with precisions that are greater than 15 nm and loglikelihoods that
are greater than 250. We do this by first building an analysis
pipeline containing **processors** to apply in sequence to the data.::

   >>> from bstore import batch, processors
   >>> precisionFilter = processors.Filter('precision', '<', 15)
   >>> llhFilter = processors.Filter('loglikelihood', '<=', 250)
   >>> pipeline = [precisionFilter, llhFilter]

Next, use an **HDFBatchProcessor** to access the database, pull out
all localization files, and apply the filters. The results are saved
as .csv files for later use and analysis.::

   >>> bp = batch.HDFBatchProcessor(dbName, pipeline)
   >>> bp.go()
   Output directory does not exist. Creating it...
   Created folder /home/douglass/src/processed_data

Inside each of the resulting subfolders you will see a .csv file
containing the filterd localization data. A more complete tutorial may
be found at
https://github.com/kmdouglass/bstore/blob/master/examples/Tutorial%202%20-%20Introduction%20to%20batch%20processing.ipynb .

Getting Help
============

If you have any questions, feel free to post them to the Google Groups
discussion board: https://groups.google.com/forum/#!forum/b-store

Bug reports may made on the GitHub issue tracker:
https://github.com/kmdouglass/bstore/issues
