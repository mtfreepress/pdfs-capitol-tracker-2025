#!/bin/bash

# create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# make scripts executable
chmod +x ./fetch_and_compress.sh
chmod +x ./deploy.sh

echo "Setup complete! To activate the virtual environment, run:"
echo "source venv/bin/activate"