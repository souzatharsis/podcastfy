# Contributor Guidelines

Thank you for your interest in contributing to Podcastfy! We welcome contributions from the community to help improve and expand this project. Please follow these guidelines to ensure a smooth collaboration process.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork locally: `git clone https://github.com/your-username/podcastfy.git`
3. Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name`

## Code Style

- Follow PEP 8 style guidelines for Python code.
- Use tabs for indentation instead of spaces.
- Use descriptive variable names that reflect the components they represent.
- Include docstrings for all functions, classes, and modules.

## Development

- Poetry is the preferred but not mandatory dependency manager. Install it with `pip install poetry`.
    - Contributors can opt to use `uv` instead and generate and push updated requirements.txt from it. 
- Sphinx is used as the documentation generator. Install it with `pip install sphinx`.
    - `make doc-gen` to generate the documentation.


## Submitting Changes

1. Commit your changes with clear, descriptive commit messages.
2. Push your changes to your fork on GitHub.
3. Submit a pull request to the main repository.

## Pre-Pull Request Checklist

1. Managing dependencies
    - Add new dependencies with `poetry add <new-dependency>` 
    - Remove a dependency with `poetry remove <dependency-name>`. 
    - Then generate requirements.txt with `poetry export -f requirements.txt --output requirements.txt --without-hashes`
2. Testing
    - Consider adding new tests at test/*.py, particularly if implementing user facing change.
    - Test locally: `poetry run pytest`
    - Tests (tests/*.py) are run automatically by GitHub Actions, double check that they pass.
3. Docs
    - Update any documentation if required README.md, usage/*.md, *.ipynb etc.
    - Regenerate documentation (/docs) if there are any changes in docstrings or modules' interface (`make doc-gen`)


## Reporting Issues

- Use the GitHub issue tracker to report bugs or suggest enhancements.
- Provide a clear and detailed description of the issue or suggestion.
- Include steps to reproduce the bug, if applicable.

## Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to abide by its terms.

## Questions?

If you have any questions or need further clarification, please don't hesitate to ask in the GitHub issues section.

Thank you for contributing to Podcastfy!
