#!/bin/bash

# Install required packages if not already installed
pip install -q requests uvicorn testcontainers

# Run the tests
echo "Running tests..."
pytest "$@" -v 