#!/bin/bash

# It assumes it has FastAPI example server running on localhost:8000

# Navigate up two parent folders
cd ../../

# Run python build command
python -m build

# Assuming the build produces a single .whl file in the dist/ directory.
# Adjust the glob pattern as needed if your package produces different files.
PACKAGE_FILE=$(ls dist/*.whl | head -n 1)

# Install the package using pip
pip install --force-reinstall "$PACKAGE_FILE"
