#!/bin/bash

# Alias for running specific unit tests
alias testit='.venv/bin/python3.12 -m unittest tests/test_content_parser.py'
export PYTHONPATH="~src/podcastfy:$PYTHONPATH"

# Add more aliases here as needed
# For example:
# alias runapp='python3 main.py'
# alias lint='flake8 .'
# alias formatcode='black .'