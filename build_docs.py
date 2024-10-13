import os
import sys
from sphinx.cmd.build import main as sphinx_main

def main():
	"""
	Wrapper function to build Sphinx documentation.
	"""
	# Change to the docs directory
	os.chdir('docs')
	
	# Run Sphinx build command
	sys.exit(sphinx_main(['-b', 'html', 'source', '_build/html']))

if __name__ == '__main__':
	main()