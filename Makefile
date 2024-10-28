lint:
	black podcastfy/*.py
	black tests/*.py
	mypy podcastfy/*.py

test:
	poetry run pytest -n auto
    
doc-gen:
	sphinx-apidoc -f -o ./docs/source ./podcastfy
	(cd ./docs && make clean && make html)
	