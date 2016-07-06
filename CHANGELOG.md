# Change Log
All notable changes to this project will be documented in this file.

## [Unreleased]
### Changed
- Simplified the code for the OverlayClusters multiprocessor.
- Individual fiducial plots now all use the same y-axis limits.

### Fixed
- fiducialLocs DataFrame belonging to `ComputeTrajectories` is now
  automatically sorted, which allows for multi-indexing.

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

[Unreleased]: https://github.com/kmdouglass/bstore/compare/v0.1.0b-rev3...HEAD
[v0.1.0b-rev3]: https://github.com/kmdouglass/bstore/compare/v0.1.0b-rev2...v0.1.0b-rev3
