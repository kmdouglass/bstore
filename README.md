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

# What is single molecule localization microscopy (SMLM)?

SMLM is a suite of super-resolution fluorescence microscopy techniques for imaging microscopic structures (like cells and organelles) with resolutions below the diffraction limit of light. A number of SMLM techniques exist, such as [fPALM](http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1635685/), [PALM](http://www.ncbi.nlm.nih.gov/pubmed/16902090), [STORM](http://www.ncbi.nlm.nih.gov/pmc/articles/PMC2700296/), and [PAINT](http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1748151/). In these microscopies, fluorescent molecules are made to "blink" on and off. A final image or dataset is computed by recording the positions of every blink for a period of time and adding together all the positions in the end.

A fantastic movie explaining how this works using the blinking lights of the Eiffel tower was created by Ricardo Henriques. You can watch it here: https://www.youtube.com/watch?v=RE70GuMCzww

# Who wrote B-Store?
[Kyle Douglass](http://kmdouglass.github.io) is the primary author of B-Store. He works at the [EPFL](http://epfl.ch/) in the lab of [Suliana Manley](http://leb.epfl.ch/).

Other contributors include:
+ [Marcel Stefko](https://people.epfl.ch/marcel.stefko?lang=en)

# What does the 'B' stand for?
Blink.