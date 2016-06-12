# Run from the bstore project root
conda build utils/anaconda --channel soft-matter

# Update path to .tar.bz2 file
conda convert --platform all ~/anaconda3/conda-bld/linux-64/bstore-0.1.0b-py35_0.tar.bz2 -o ~/src/bstore-build

# Upload to anaconda
# anaconda login
anaconda upload ../bstore-build/linux-64/bstore-0.1.0b-py35_0.tar.bz2
anaconda upload ../bstore-build/linux-32/bstore-0.1.0b-py35_0.tar.bz2
anaconda upload ../bstore-build/win-64/bstore-0.1.0b-py35_0.tar.bz2
anaconda upload ../bstore-build/win-32/bstore-0.1.0b-py35_0.tar.bz2
anaconda upload ../bstore-build/osx-64/bstore-0.1.0b-py35_0.tar.bz2 
