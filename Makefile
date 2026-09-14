# Makefile for CodeJail
.PHONY: clean dev-requirements quality requirements test test_no_proxy \
        test_proxy upgrade upgrade

clean:
	find src/codejail -name '*.pyc' -exec rm -f {} +
	find src/codejail -name '*.pyo' -exec rm -f {} +
	find src/codejail -name '__pycache__' -exec rm -rf {} +


test: test_no_proxy test_proxy

test_no_proxy:
	@echo "Running all tests with no proxy process"
	CODEJAIL_PROXY=0 pytest --junitxml=reports/pytest-no-proxy.xml --log-level=DEBUG

test_proxy:
	@echo "Running all tests with proxy process"
	CODEJAIL_PROXY=1 pytest --junitxml=reports/pytest-proxy.xml --log-level=DEBUG

upgrade: ## update python dependencies
	uv run --with edx-lint edx_lint write_uv_constraints pyproject.toml
	uv lock --upgrade

quality: ## check coding style with pycodestyle and pylint
	pycodestyle src/codejail *.py
	isort --check-only --diff src/codejail *.py
	pylint src/codejail *.py

isort: ## apply automatic import sorting
	isort --recursive src/codejail *.py

requirements: dev-requirements

dev-requirements:
	uv sync --group dev
