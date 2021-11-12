SRC = $(wildcard ./*.ipynb)

all: hecss docs

hecss: $(SRC)
	nbdev_build_lib
	touch hecss

docs_serve: docs
	cd docs && bundle exec jekyll serve

docs: $(SRC)
	nbdev_build_docs
	touch docs

test:
	nbdev_test_nbs

release: pypi
	nbdev_bump_version

pypi: dist
	twine upload --repository hecss dist/*

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist
