# B-Store
[![Build Status](https://travis-ci.com/kmdouglass/bstore.svg?token=wpszvKaNd7qmZqYsAqpT&branch=development)](https://travis-ci.com/kmdouglass/bstore)

# What is B-Store?

[B-Store](https://github.com/kmdouglass/bstore) is a lightweight data management and analysis library for single molecule localization microscopy (SMLM). It serves two primary roles:

1. To organize SMLM data inside a database for fast and easy information retrieval and storage.
2. To facilitate the analysis of high content SMLM datasets.

## What are the design criteria that guide B-Store's development?
To realize these roles, B-Store is designed to meet these important criteria:

+ Experimental datasets must be combined into a database-like structure that is easily readable by both humans and computers.
+ Access and processing of data must be fast, regardless of the size of the dataset.
+ [Data provenance](https://en.wikipedia.org/wiki/Data_lineage) must be preserved throughout the organization and analysis pipeline.
+ B-Store should not enforce standards that force scientists to adopt file formats, naming conventions, or software packages that differ from the ones they already use, except when it is absolutely necessary to achieve its roles.
+ B-Store should be extensible to adapt to the changing needs of scientists using SMLM.
+ Above all else, B-Store should make it easy to organize and document data and analysis pipelines to improve the reproducibility of SMLM experiments.

Of course, the changing needs of scientists means that B-Store will always be evolving to meet these criteria.

## What doesn't B-Store do?
B-Store is efficient and fast because its scope is limited to SMLM data organization and analysis. In particular, B-Store does not:

+ Calculate localizations from raw images.
+ Control microscopy hardware.
+ Provide database-like storage for core facilities.
+ Generate any data or results for you. (Sorry.)

If you would like to compute localizations from raw images, there are a number of available software packages that have been developed by great people. A good place to start learning about them is here: [SMLM Software Benchmarking by the Biomedical Imaging Group at EPFL](http://bigwww.epfl.ch/smlm/index.html#&panel1-1).

Microscope hardware and acquisition control is often performed inside either commercial or custom-written software packages. A great open source project with a lot of support and that we personally use is [Micro-Manager](https://micro-manager.org/).

If you are a core facility manager and looking for a database system for fluorescence microscopy data, [OMERO](https://www.openmicroscopy.org/site) is a well-developed project that may suit your needs. Additionally, there has been some discussion on a SMLM standard format and incorporating it into OMERO (see this thread at http://lists.openmicroscopy.org.uk/pipermail/ome-devel/2015-July/003410.html). In our experience, OMERO requires infrastructure in the form of hardware and personnel that small labs may not be able to satisfy. Furthermore, this standard format does not yet exist as of June, 2016. In anticipation of this format, B-Store is designed to be as agnostic to file formats as possible so that it may adapt as the field evolves.

## How is B-Store implemented?
B-Store is written in the [Python](https://www.python.org/) programming language (version 3) and relies heavily on a datatype known as a DataFrame. DataFrames and their functionality are provided by the [Pandas](http://pandas.pydata.org/) library and in many ways work like Excel spreadsheets but are much, much faster. Pandas is optimized and used extensively for big data analytics, among other things.

In addition to Pandas, B-Store implements features provided by numerous scientific, open source Python libraries like [numpy](http://www.numpy.org/) and [matplotlib](http://matplotlib.org/).

### I want to use B-Store, but I don't know Python.
If you don't know Python, you can still use B-Store in a number of ways.

The easiest way is to explore the [Jupyter notebooks](http://jupyter.org/) in the *examples* folder. Find an example that does what you want, then modify the relevant parts, such as file names. Then, simply run the notebook.

You may also wish to use B-Store's database system, but not its analysis tools. In this case, you can use the notebooks to build your database, but access and analyze the data from the programming language of your choice, such as MATLAB. B-Store currently provides functionality for a database stored in an HDF file, but the Database interface may be

A third option is to call the Python code from within another language. Information for doing this in MATLAB may be found at the follow link, though we have not yet tested this ourselves: http://www.mathworks.com/help/matlab/call-python-libraries.html

Of course, these approaches will only take you so far. Many parts of B-Store are meant to be customized to suit each scientist's needs, and these customizations are most easily implemented in Python. Regardless, the largest amount of customization you will want to do will likely be to write a `Parser`. A `Parser` converts raw acquisition and localization data into a format that can pass through the database interface (known as a `DatabaseAtom`). If your programming language can call Python and access the `DatabaseAtom` and `Database` interfaces, then you can write the parser in the language of your choice and then pass the parsed data through these interfaces to build your database.

# What is the logic behind the B-Store design?
B-Store is designed to search specified directories on your computer for files associated with an SMLM experiment, such as those containing raw localizations and widefield images. These files are passed through a `Parser`, which converts them into a format suitable for insertion into a database. It does this by ensuring that the files satisfy the requirements of an interface known as a `DatabaseAtom`. Data that implements this interface may pass into and out of the database; data that does not implement the interface cannot. You can think of the `DatabaseAtom` interface like a guard post at a government research facility. Only people with an ID badge for that facility (the interface) may enter. In principle, B-Store does not care about the data itself or the details of the database (HDF, SQL, etc.).

At the time this README file was written, the `DatabaseAtom` interface consisted of the following properties:

1. **acquisition ID** - integer identifying a specific acquisition
2. **data** - the actual data to insert into the database, which can be numeric or otherwise
3. **prefix** - a descriptive name for the acquisition, such as the cell type or condition
4. **dataset type** - The type of data contained in the atom (currently localizations, metadata, or widefield images)
5. channel ID - the wavelength being imaged
6. position ID - A single integer or integer pair identifying the position on the sample
7. slice ID - An integer identifying the axial slice acquired

The first four properties in bold are required; the last three are optional.

There are three important advantages to enforcing an interface such as this.

1. The computer will always know what kind of data it is working with and how to organize it.
2. The format of the data that you generate in your experiments can be made independent of the database, so you can do whatever you want to it. The `Parser` ensures that it is in the right format only at the point of database insertion.
3. The nature of the database and the types of data it can handle can grow and change in the future with minimal difficulty.

The logic of this interface is described graphically below. The raw images on top pass through the `Parser` and into the database, where they are organized into acquisition groups. Each group is identified by a name (**prefix**). A group consists of a number of datasets that are uniquely identified by their acqusition group **prefix**, **acquisition ID**, and **dataset type**. The other identifiers are optional. The database is therefore a collection of hierarchically arranged datasets that are uniquely determined by these identifiers.

![B-Store design logic.](/design/dataset_logic.png)


# What is single molecule localization microscopy (SMLM)?

SMLM is a suite of super-resolution fluorescence microscopy techniques for imaging microscopic structures (like cells and organelles) with resolutions below the diffraction limit of light. A number of SMLM techniques exist, such as [fPALM](http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1635685/), [PALM](http://www.ncbi.nlm.nih.gov/pubmed/16902090), [STORM](http://www.ncbi.nlm.nih.gov/pmc/articles/PMC2700296/), and [PAINT](http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1748151/). In these microscopies, fluorescent molecules are made to "blink" on and off. A final image or dataset is computed by recording the positions of every blink for a period of time and adding together all the positions in the end.

A fantastic movie explaining how this works using the blinking lights of the Eiffel tower was created by Ricardo Henriques. You can watch it here: https://www.youtube.com/watch?v=RE70GuMCzww

# Who wrote B-Store?
[Kyle Douglass](http://kmdouglass.github.io) is the primary author of B-Store. He works at the [EPFL](http://epfl.ch/) in the lab of [Suliana Manley](http://leb.epfl.ch/).

Other contributors include:
+ [Marcel Stefko](https://people.epfl.ch/marcel.stefko?lang=en)

# What does the 'B' stand for?
Blink.