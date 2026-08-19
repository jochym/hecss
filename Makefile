# Makefile for hecss marimo + Quarto + quartodoc workflow
# Replaces nbdev-prepare

.PHONY: prepare test build-package build-docs clean publish

# Default target
prepare: build-package test build-docs

# Build the hecss package from notebooks
build-package:
	uv run python scripts/build_package.py

# Run tests on notebooks
test:
	uv run python -m pytest notebooks/ -v

# Build documentation (export notebooks + quartodoc + quarto render)
build-docs:
	uv run python scripts/build_docs.py

# Clean generated files
clean:
	rm -rf hecss/*.py
	rm -rf _quarto/*.qmd
	rm -rf _docs
	rm -rf reference

# Publish to PyPI
publish: prepare
	uv build
	uv publish

# Install in development mode
install-dev:
	uv pip install -e .

# Run a specific notebook with marimo
run-%:
	uv run marimo run notebooks/$*.py

# Edit a specific notebook with marimo
edit-%:
	uv run marimo edit notebooks/$*.py

# Check notebook syntax
check-%:
	uv run marimo check notebooks/$*.py

# Export a single notebook to QMD
export-%:
	uv run marimo export md notebooks/$*.py -o _quarto/$*.qmd --flavor qmd