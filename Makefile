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
    
test_asap:
	nbdev_test_nbs --flags asap

test_vasp:
	nbdev_test_nbs --flags vasp

release: pypi conda_release
	nbdev_bump_version

conda_meta:
	fastrelease_conda_package --do_build false
	sed -i -e 's/APACHE/GPL3/g' \
		-e 's/Apache Software/GPL-3.0-or-later/g' \
		-e 's/dev_url: .*/dev_url: http:\/\/gitlab.com\/jochym\/hecss\//g' \
		conda/hecss/meta.yaml

conda_release: conda_meta
	conda mambabuild --python 3.8 conda/hecss

pypi: dist
	twine upload --repository hecss dist/*

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist
	conda build purge
