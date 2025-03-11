import os
import pkgutil

def generate_api_docs(package_name):
	"""Generate reStructuredText API documentation for a given Python package.

    This function creates a directory named 'docs/source/api' if it doesn't exist,
    and generates reStructuredText (.rst) files for each module in the specified package.
    The main API documentation page, 'index.rst', is also generated and includes each
    module's documentation as a part of a toctree.

    Args:
        package_name (str): The name of the package to generate API documentation for.

    Note:
        Ensure that the package is installed and accessible in the Python environment
        where this function is executed."""
	# Get the package
	package = __import__(package_name)

	# Create the api directory if it doesn't exist
	api_dir = 'docs/source/api'
	os.makedirs(api_dir, exist_ok=True)

	# Generate the main API page
	with open(f'{api_dir}/index.rst', 'w') as f:
		f.write(f"{package_name} API\n")
		f.write("=" * (len(package_name) + 4) + "\n\n")
		f.write(".. toctree::\n")
		f.write("   :maxdepth: 2\n\n")

	# Iterate through all modules in the package
	for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
		with open(f'{api_dir}/{module_name}.rst', 'w') as f:
			f.write(f"{module_name}\n")
			f.write("=" * len(module_name) + "\n\n")
			f.write(f".. automodule:: {module_name}\n")
			f.write("   :members:\n")
			f.write("   :undoc-members:\n")
			f.write("   :show-inheritance:\n")

		# Add the module to the main API page
		with open(f'{api_dir}/index.rst', 'a') as f:
			f.write(f"   {module_name}\n")

def main():
	"""Generate API documentation for a specified package.

    This function triggers the generation of API documentation for the specified
    package. Replace 'podcastfy' with the actual name of the package you wish 
    to document.

    Args:
        None

    Returns:
        None"""
	generate_api_docs('podcastfy')  # Replace 'podcastfy' with your actual package name

if __name__ == "__main__":
	main()