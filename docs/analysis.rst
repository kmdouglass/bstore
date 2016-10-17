.. -*- mode: rst -*-
   
****************************
Analysis Routines in B-Store
****************************

:Author: Kyle M. Douglass
:Contact: kyle.m.douglass@gmail.com
:organization: École Polytechnique Fédérale de Lausanne (EPFL)
:status: Revision: 0
:date: 2016-08-06

:abstract:

   A brief overview of performing simple and batch analyses in B-Store
   is provided.
   
.. meta::
   :keywords: faq
   :description lang=en: Documentation on B-Store analysis tools.
	      
.. contents:: Table of Contents

Analyzing SMLM Experiments with B-Store
=======================================

First and foremost, B-Store is a tool for structuring data from SMLM
experiments. With structured data, analysis of large datasets becomes
easier because we can write programs to automatically take just the
data we want and process it or make reports. The data is always
organized in the same way, so our analysis routines can be easily
adapted when new data arrives.

B-Store provides analysis routines as a secondary feature. Many
software packages exist for analyzing SMLM data, and B-Store is not
intended to replace them. Rather, B-Store provides common processing
routines as a convenience--such as filtering or merging
localizations--and less common processing routines for specialized
analyses performed in the authors' laboratories.

Batch Processing
----------------

B-Store currently provides two batch processors for working with SMLM
data: `HDFBatchProcessor`_, for extracting data from B-Store HDF
Datastores and processing them, and `CSVBatchProcessor`_, for applying
the same processing pipeline to .csv files spread across a directory
tree.

.. _HDFBatchProcessor: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.batch.HDFBatchProcessor
.. _CSVBatchProcessor: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.batch.CSVBatchProcessor

The operation of a batch processor is simple: first, it accepts an
analysis pipeline and a datastore or directory that contain at least
one file corresponding to an SMLM dataset. The pipeline is a list of
`B-Store processors`_ that modify a DataFrame containing
localizations. Each processor is applied to a single dataset
sequentially, starting from the first processor in the list.

Next, the batch processor accumulates a list of all the localization
files in the database. If using the CSVBatchProcessor, it finds all
files ending in the string parameter `suffix`. For example, if your
localization files end in `locResults.csv`, you can set `suffix =
'locResults.csv'` and the batch processor will find these files in the
specified folder **and all subfolders.** If using the
HDFBatchProcessor, you can specify localization files using the
`searchString` parameter.

.. _B-Store processors: http://b-store.readthedocs.io/en/latest/bstore.html#module-bstore.processors

Once the list of datasets is built, the batch processor loops over
each dataset, applying the processors in the pipeline one at a time to
the DataFrame. Currently, the output results are written to new .csv
files in a folder specified in the `outputDirectory` parameter to the
constructor of both batch processors. This feature allows you to
perform analyses with different pipelines on the same database.

For an example of how to perform batch processing in B-Store, see the
`Jupyter notebook tutorial`_.

.. _Jupyter notebook tutorial: https://github.com/kmdouglass/bstore/blob/master/examples/Tutorial%202%20-%20Introduction%20to%20batch%20processing.ipynb

Analyzing Single Datasets
-------------------------

Single datasets may be retrieved from a B-Store database for analysis
using the `get() method`_ of the Database class.

.. _get() method: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.database.Database.get

Processing Localizations and other Data
=======================================

Processors
----------

A `processor`_ is a simple class for processing localization
datasets. Its behavior is controlled by zero or more attributes that
are set in the processor's constructor. A processor is callable in
that it is used like a function; when doing so, it **always accepts a
single Pandas DataFrame as an input**.::

  >>> import bstore.processors as proc
  >>> myFilter = proc.Filter('precision', '<', 15)
  >>> filterData = myFilter(df)

In the above example, we create a filter processor called *myFilter*
whose constructor takes three arguments: the name of column to filter
on, a string specifying the comparison operator (in this case
less-than) and a numeric value. All rows in the 'precision' column
will have values less than 15 after this filter is applied.

After creating the processor, you apply it to a Pandas DataFrame by
using it like a function. In the above example, we pass a DataFrame
named `df` to `myFilter` and store the processed DataFrame in
`filterData`.

When creating your own processor, you can achieve this function-like
behavior of a class by specifying the behavior inside the class's
`__call__()` method. For more information, see the `Python
documentation`_.

.. _Python documentation: https://docs.python.org/3/reference/datamodel.html#object.__call__

A complete list of processors and their behavior may be found in the
`processor`_ module index.

.. _processor: http://b-store.readthedocs.io/en/latest/bstore.html#module-bstore.processors

Multi-Processors
----------------

Multi-processors are similar to processors, except for two points:

1. they accept multiple inputs instead of a single DataFrame, and
2. they may take user-input and thus may not necessarily be used in
   batch processing.

Two examples of multi-processors are `AlignToWidefield`_ and
`OverlayClusters`_. `AlignToWidefield` determines the global offset
between localizations and a widefield image by using a simple
FFT-based cross-correlation routine.

`OverlayClusters` is a very useful analysis tool for displaying
clustered localizations on top of a widefield image. This tool may be
used to navigate through different clusters of localizations, manually
filter clusters from the dataset, and to append numeric labels to
clusters for manual segmentation. Generally, `AlignToWidefield` is
before `OverlayClusters`.

.. _AlignToWidefield: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.multiprocessors.AlignToWidefield
.. _OverlayClusters: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.multiprocessors.OverlayClusters

Performing Analyses Outside of B-Store
======================================

B-Store databases use the HDF format and are therefore readable by
many scientific libraries. You may analyze your data in any of these
if the B-Store analysis tools do not suit your purposes.

