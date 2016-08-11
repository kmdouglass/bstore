.. -*- mode: rst -*-
   
*****************
B-Store Databases
*****************

:Author: Kyle M. Douglass
:Contact: kyle.m.douglass@gmail.com
:organization: École Polytechnique Fédérale de Lausanne (EPFL)
:revision: $Revision: 0 $
:date: 2016-08-11

:abstract:

   B-Store uses the HDF file format, which means it may be used with
   other software programs for bio-image analysis.
   
.. meta::
   :keywords: b-store
   :description lang=en: Using B-Store with other software.
	      
.. contents:: Table of Contents

Using B-Store with Other Software
=================================

B-Store databases use the `HDF`_ file format for data storage. This
means that any software package that can read from HDF files can also
read B-Store databases.

.. _HDF: https://www.hdfgroup.org/

ImageJ and Fiji
---------------

Widefield images found inside a B-Store database may be opened in
ImageJ and Fiji using the `HDF5 Plugin for ImageJ and Fiji`_. When
using the GUI loader, use the option **individual hyperstacks (custom
layout)** with ``yz`` as the **data set layout** argument.

This functionality requires that the image data in the HDF file
possess an attribute called ``element_size_um`` that contains three
floating point numbers corresponding to the size of a pixel in z, y,
and x-directions. There are three ways that this attribute may be
created when the database is built:

1. By specifying the `HDFDatabase`_ ``widefieldPixelSize`` property,
   which is a two-element tuple of the x- and y- pixel sizes.
2. If ``widefieldPixelSize`` is None, the pixel size is extracted from
   the Micro-Manager metadata in the field specified by
   ``__MM_PixelSize__`` in B-Store's config.py.
3. Failing this, the pixel size is extracted from the OME-XML
   metadata.
3. Failing this, the attribute ``element_size_um`` is not set.

.. _HDFDatabase: http://b-store.readthedocs.io/en/latest/bstore.html#bstore.database.HDFDatabase
.. _HDF5 Plugin for ImageJ and Fiji: http://lmb.informatik.uni-freiburg.de/resources/opensource/imagej_plugins/hdf5.html

