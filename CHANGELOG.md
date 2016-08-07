# Change Log
All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- OME-XML and Micro-Manager metadata are now recorded in the same HDF
  group as the image data for widefieldImage dataset types.
- B-Store dataset IDs are now saved as attributes of the
  widefieldImage groups in the HDF file.

### Changed
- Reformatted docstrings to better match the
  [NumPy format](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt#documenting-classes).
- Widefield image data is now saved with the dataset name `image_data`
  inside HDF files. Previously, it was saved as `widefield_` plus the
  channelID, which made little sense, especially if the channelID was
  not specified.

### Fixed
- Database.query() no longer returns widefieldImage datasets twice.

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

[Unreleased]: https://github.com/kmdouglass/bstore/compare/v0.1.1...HEAD
[v0.1.1]: https://github.com/kmdouglass/bstore/compare/v0.1.0...v0.1.1
[v0.1.0]: https://github.com/kmdouglass/bstore/compare/v0.1.0b-rev3...v0.1.0
[v0.1.0b-rev3]: https://github.com/kmdouglass/bstore/compare/v0.1.0b-rev2...v0.1.0b-rev3
