.. -*- mode: rst -*-
   
*****************
B-Store Databases
*****************

:Author: Kyle M. Douglass
:Contact: kyle.m.douglass@gmail.com
:organization: École Polytechnique Fédérale de Lausanne (EPFL)
:status: in progress
:date: 2016-07-23

:abstract:

   The logic behind B-Store databases is presented in this
   document. The HDF file type is briefly explained, followed by the
   organization of data within the database.
   
.. meta::
   :keywords: b-store, database
   :description lang=en: Documentation on B-Store databases.
	      
.. contents:: Table of Contents

Introduction to B-Store Databases
=================================

A single high-throughput SMLM experiment can generate hundreds or even
thousands of different files containing different types of
data. Analyzing this data requires that the files are sorted and
organized in a well-structured way that is understandable by both
humans and machines. A B-Store database fulfills this role as a
structured container for heterogeneous SMLM data.

In basic terms, a B-Store *database* is a collection of individual
*datasets*. Each dataset possesses identifiers that uniquely identify
it within the database. A dataset also provides a container for the
actual experimental data that it is holding, such as localizations or
widefield images.

Datasets
========

A `Dataset`_ is a single, generalized dataset that can be stored in a
B-Store database. It is "general" in the sense that it can represent
one of a few different types of data (e.g. localizations, metadata, or
widefield images). It is a subclass of a `DatabaseAtom`_. Both of
these classes provide functionality to store the identifiers for a
dataset and return them in a format that is used by both the user and
by other parts of B-Store.

.. _Dataset: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.database.Dataset
.. _DatabaseAtom: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.database.DatabaseAtom

Dataset IDs
-----------

A dataset is uniquely defined by the following fields (the first
three--prefix, acqID, and datasetType-- are required).

prefix
    A descriptive name given to the dataset.

acqID
    An integer that specifies the acquisition number of the dataset.

datasetType
    A string. Currently must be one of 'locResults', 'locMetadata', or
    'widefieldImage'. The up-to-date list of accepted strings is in
    `config.py`_ in the variable __Types_Of_Atoms__.

channelID
    (optional) A string that specifies the fluorescence channel that
    the dataset was acquired in. The list of channel IDs is in
    `config.py`_ in the variable __Channel_Identifier__.

dateID
    (optional) A string in the format YYYY-MM-DD.

posID 
    (optional) A one or two-element tuple of integers specifying the
    position of the field of view of the dataset.

sliceID
    (optional) An integer identifying the the axial slice of the
    dataset.

.. _config.py: https://github.com/kmdouglass/bstore/blob/master/bstore/config.py

Hierarchy of Dataset IDs
------------------------

All datasets with the same prefix are organized into the same
**acquisition group**. Within an acquisition group, datasets are
specified according to their acqID.

For example, let's say we take three widefield images of Cos7 cells
from the same coverslip during the same experiment. In the database,
each image will have the same prefix, such as 'Cos7'. The individual
images however will have three different acqID's. (Most likely they
will be 1, 2, and 3, but they need not start at 1 or be sequential.)

If two datasets have the same prefix and acqID but different
datasetType's, then they will be understood to have come from the same
field of view. This allows widefield images to be grouped with their
corresponding localizations within the database. As an example, we
might have two datasets in our database where both have 'HeLa' as a
prefix and 1 as the acqID, but one has 'locResults' as its datsetType
and the other 'widefieldImage'.

Finally, the optional identifiers can further divide datasets that
have the same prefix, acqID, and datasetTypes.

Database Types
==============

In the B-Store code, a generic database is represented by the
`Database`_ class. This is a metaclass that specifies all the
functions that a B-Store database must have, but does not necessarily
implement these functions or determine what container the database is
stored in.

The `HDFDatabase`_ class is a subclass of Database and allows for the
creation of a database inside a `HDF`_ container. HDF is a
high-performance file type used in scientific and numerical
computing. It is considered a standard file type in scientific circles
and is widely supported by many programming environments. One
advantage of HDF containers is that you are not required to use
B-Store code to access the data in a B-Store database. Any software
that can read or modify HDF files will do.

In the future, databases utilizing other modalities, such as SQLite,
may be added by extending the Database class.

.. _Database: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.database.Database
.. _HDFDatabase: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.database.HDFDatabase
.. _HDF: https://www.hdfgroup.org/

HDFView
-------

`HDFView`_ is a useful utility for viewing the contents of a HDF
container. It is freely available and recommended for trouble
shooting.

We will use screenshots taken from HDFView to explain how data is
sorted inside a B-Store database.

.. _HDFView: https://www.hdfgroup.org/products/java/hdfview/


