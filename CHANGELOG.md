# Change Log
All notable changes to this project will be documented in this file.

## [v1.1.0]
### Added
- `HDFDatastore` objects are now persistent; their state is saved to
  the HDF file every time a dataset is put into the datastore, which
  includes datastore builds.
- There are now so-called `Reader` objects for reading raw
  localization files. A `Reader` is passed as a keyword argument to a
  `Parser`'s `readFromFile()` routine and may be used to read
  different types of localization file formats.
- `HDFDatastore.build()` now allows one to specify Readers for
  different DatasetTypes via the `readers` parameter. By default, it
  is an empty dict.
- Currently, `CSVReader` for reading general CSV files and
  `JSONReader` for reading JSON data are available. For the moment,
  these are only usable for Localization, FiducialTracks, and
  AverageFiducial DatasetTypes; they are not accessible through the
  GUI. More specific implmentations of various `Reader` objects should
  follow in later versions. The `CSVReader` uses the Pandas
  [read_csv](http://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_csv.html)
  method. Any keyword argument that `read_csv()` takes may be passed
  as a keyword argument to `readFromFile()`. Likewise, the
  `JSONReader` uses the Pandas
  [read_json](http://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_json.html)
  method and is similarly customizable.
- The
  [examples](https://github.com/kmdouglass/bstore/tree/master/examples)
  folder now includes a Jupyter notebook demonstrating how to write
  your own Reader.
- An explanation on how to adjust the image colormap and max/min
  values was added to the
  [widefield cluster overlay example](https://github.com/kmdouglass/bstore/blob/master/examples/Localization%20Overlays%20on%20Widefield%20Images.ipynb).
  This functionality requires Matplotlib 2.0 or greater.
- A dataset ID known as `replicateID` was added to the end of the list
  DatasetIDs. It is an integer that is intended to denote datasets
  with the same prefix and acquisition number but different
  samples/biological replicates.

### Changed
- `HDFDatastore` now require Python *with...as...* statements
  (i.e. `HDFDatastore`'s are now context managers) when putting
  datasets or building a datastore. The reason for this is that it's
  easier to lock the HDF file when it's used as a context manager,
  preventing multiple HDFDatastore objects that point to the same file
  from going out of sync with the persistent representation inside the
  file.
- The order of the fields in the GUI's HDFDatastore build dialog was
  changed to better match the inputs->parameters->outputs mental model
  of how the build process occurs.
- HDF keys generated for datasets containing a non-empty dateID were
  changed to improve the consistency of the key naming
  convention. Now, dateID follows sliceID in the list of optional IDs
  that label a dataset. It is no longer injected in as an additional
  group in a key. The `dateID` is intended to denote the exact same
  field of view taken on different days.

### Fixed
- Redundant calls to `readFromFile` inside the Parsers was removed.

## [v1.0.1]
## Added	
- Added a unit test for the OverlayClusters multiprocessor.

### Fixed
- Fixed a bug in `OverlayClusters` that was related to a change in
  Pandas 0.19.1 and the np.min() function was fixed.
- Localizations not used for spline fitting in the
  `DefaultDriftComputer` now appear as gray, rather than blue, when
  `plotFiducials()` is called.
- The `PositionParser` was not correctly parsing file names on
  Windows because */* was the assumed separator. This is now fixed.
	
## [v1.0.0]
### Added
- `PositionParser` was added for parsing files whose names contain
  fields spaced by string separators and whose positions correspond to
  different dataset IDs. For example, the filename `HeLa_1_A647_0.csv`
  may be split at each underscore and possess four fields that would
  serve as possible IDs: `HeLa`, `1`, `A647`, and `0`.
- There is now a GUI interface for building HDF datatstores.
- The `__Verbose__` flag was added to config.py. Setting this flag to
  true will print more information to the console to assist with
  debugging.
- `HDFDatastore` now supports iteration via the `__iter__()` magic
  method and direct inspection of the number of datasets using `len()`
  via the `__len__()` magic method. Furthermore, it supports
  integer-based indexing via `__getitem__()`. This means that one may
  loop over and filter datasets using standard Python operations on
  iterables and sequences.
- `DefaultDriftComputer` now accepts a `maxRadius`
  attribute. Localizations in a region of interest that lie further
  than a distance equal to `maxRadius` from the localizations' center
  of mass are not included in the drift trajectory computation.
- `ComputeTrajectories` objects, such as `DefaultDriftComputer`, now
  have reset() methods to reset them to their initial state.
- Added an example on merging localizations to the Jupyter Notebook
  [examples folder](https://github.com/kmdouglass/bstore/tree/master/examples).

### Changed
- `Database` and `HDFDatabase` were renamed to `Datastore` and
  `HDFDatastore`, respectively. The database module has not changed
  names.
- Datasets were simplified into a parent class and child
  classes. Child classes were previously called generics; now each
  child class represents its own type of dataset. This effectively
  decouples dataset information from the Datastore and Parser classes.
- get() and put() behaviors were decoupled from the HDFDatastore. Now,
  each Dataset knows how to get and put its down data from the
  Datastore. HDFDatastore now only manages the identification and
  sorting of Datasets.
- readFromFile() behavior was decoupled from the Parser class. Each
  Dataset now knows how to read and write its own data from files.
- The channel identifier in keys of a `HDFDatastore` object are now
  identified by the `Channel` string. This was done for consistency
  with the other identifiers and to decouple and remove
  `__Channel_Identifier__` from B-Store completely. B-Store is now
  agnostic about channels and does not require them to be added in the
  config file.

### Removed
- Generic dataset types were removed. This eliminates the distinction
  that locResults, locMetadata, and widefieldImage had from other
  types of datasets. Now, all datasets subclass the `Dataset` class
  and have no special distinction over one another.
- MMParser was moved to an independent LEB extensions module because
  it is highly unlikely that any other group would use its naming
  conventions. The new module may be found here:
  https://github.com/kmdouglass/bsplugins-leb

## [v0.2.1]
### Added
- Generic datasetTypes are now available. These allow users to easily
  add new datasetTypes to the HDF database. Furthermore, they decouple
  the put() and get() behaviors from the database so that each
  datasetType knows how to handle its own data.
- Added `__version__` field to all modules.
- MergeFangTS stats computer for computing statistics on merged
  localizations in Fang's ThunderSTORM column format.

### Changed
- The `particle` column is now saved when using the MergeFang stats
  computer with the Merge processor and CSVBatchProcessor. Previously,
  it was not being saved because the the stats computer was making it
  an index of the output DataFrame; the CSVBatchProcessor does not
  save DataFrame indexes.
- Merge processor now accepts a coordinate column name parameter for
  merging columns with custom names.
- Merge processor attributes are now public.

## [v0.2.0]
### Added
- OME-XML and Micro-Manager metadata are now recorded in the same HDF
  group as the image data for widefieldImage dataset types.
- B-Store dataset IDs are now saved as attributes of the
  widefieldImage groups in the HDF file.
- HDFDatabase now accepts a `widefieldPixelSize` parameter that writes
  pixel size attributes allowing widefield images to be opened in
  other software environments.
- Added an example Jupyter notebook on using the cluster/widefield
  overlays.
- Created a new EstimatePhotons multiprocessor for estimating
  background-corrected photon counts from fluorescent spots in
  widefield images.

### Changed
- Reformatted docstrings to better match the
  [NumPy format](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt#documenting-classes).
- Widefield image data is now saved with the dataset name `image_data`
  inside HDF files. Previously, it was saved as `widefield_` plus the
  channelID, which made little sense, especially if the channelID was
  not specified.
- Database queries now work by reading B-Store HDF attributes instead
  of HDF5 group/dataset names. They now work for locMetadata as well.

### Fixed
- Database.query() no longer returns widefieldImage datasets twice.
- Bug related to transposition of the widefield image used to find
  the center location is fixed in AlignToWidefield multiprocessor.

## [v0.1.1]
### Added
- docs folder
- AlignToWidefield multiprocessor for aligning localizations to a
  widefield image.

### Changed
- Exceptions caught during database builds now describe the source of
  the error in more detail.
- README.md was condensed. Most information was moved to RTD.
- OverlayClusters multiprocessor shifts displayed localizations by
  half a pixel in each direction towards the origin. This accounts for
  the fact that matplotlib's imshow places pixel centers at the
  integer coordinates, not the pixel edges. The shifts are only
  applied for visualization; they do not affect the input DataFrame.

### Fixed
- Anaconda downloads are forced to use scipy<=0.17.1 until the recent
  bug related to Pandas, Scipy, and trackpy is fixed. See
  https://github.com/soft-matter/trackpy/issues/389 for more
  information.
	
## [v0.1.0]
### Added
- COPYRIGHT.txt

### Changed
- Simplified the code for the OverlayClusters multiprocessor.
- Individual fiducial plots now all use the same y-axis limits values.
- Default value for the zeroFrame parameter of `DefaultDriftComputer`
  is now 1000 instead of 0. A warning is raised if zeroFrame lies
  outside the allowable range of frame numbers.

### Fixed
- fiducialLocs DataFrame belonging to `ComputeTrajectories` is now
  automatically sorted, which allows for multi-indexing.
- Fixed bug in `DefaultDriftComputer` related the y-axis offset of the
  splines and fiducial localizations.
- Database build no longer fails completely when placing metadata
  into the database and localization results files are missing.

## [v0.1.0b-rev3]
### Added
- CHANGELOG.md.
- `ComputeTrajectories` metaclass and `DefaultDriftComputer` subclass
  to processors module for computing drift trajectories from one or
  more fiducials.
- Example of the new fiducial drift correction processor in
*Fiducal-based Drift Correction.ipynb*.

### Changed
- Simplified `FiducialDriftCorrect` processor.

### Fixed
- Fixed broken links in README.md.
- Added tables dependency for Windows builds.

[Unreleased]: https://github.com/kmdouglass/bstore/compare/v1.1.0...HEAD
[v1.1.0]: https://github.com/kmdouglass/bstore/compare/v1.0.1...v1.1.0
[v1.0.1]: https://github.com/kmdouglass/bstore/compare/v1.0.0...v1.0.1
[v1.0.0]: https://github.com/kmdouglass/bstore/compare/v0.2.1...v1.0.0
[v0.2.1]: https://github.com/kmdouglass/bstore/compare/v0.1.1...v0.2.0
[v0.2.0]: https://github.com/kmdouglass/bstore/compare/v0.1.1...v0.2.0
[v0.1.1]: https://github.com/kmdouglass/bstore/compare/v0.1.0...v0.1.1
[v0.1.0]: https://github.com/kmdouglass/bstore/compare/v0.1.0b-rev3...v0.1.0
[v0.1.0b-rev3]: https://github.com/kmdouglass/bstore/compare/v0.1.0b-rev2...v0.1.0b-rev3
