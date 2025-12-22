# Makefile for CodeJail
.PHONY: clean dev-requirements quality requirements test test_no_proxy \
        test_proxy upgrade upgrade

clean:
	find codejail -name '*.pyc' -exec rm -f {} +
	find codejail -name '*.pyo' -exec rm -f {} +
	find codejail -name '__pycache__' -exec rm -rf {} +


test: test_no_proxy test_proxy

test_no_proxy:
	@echo "Running all tests with no proxy process"
	CODEJAIL_PROXY=0 pytest --junitxml=reports/pytest-no-proxy.xml --log-level=DEBUG

test_proxy:
	@echo "Running all tests with proxy process"
	CODEJAIL_PROXY=1 pytest --junitxml=reports/pytest-proxy.xml --log-level=DEBUG

COMMON_CONSTRAINTS_TXT=requirements/common_constraints.txt
.PHONY: $(COMMON_CONSTRAINTS_TXT)
$(COMMON_CONSTRAINTS_TXT):
	wget -O "$(@)" https://raw.githubusercontent.com/edx/edx-lint/master/edx_lint/files/common_constraints.txt || touch "$(@)"

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: $(COMMON_CONSTRAINTS_TXT)
	## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	pip install -q -r requirements/pip_tools.txt
	pip-compile --allow-unsafe --rebuild --annotation-style=line --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	pip install -q -r requirements/pip_tools.txt
	pip-compile --annotation-style=line --upgrade -o requirements/tox.txt requirements/tox.in
	pip-compile --annotation-style=line --upgrade -o requirements/testing.txt requirements/testing.in
	pip-compile --annotation-style=line --upgrade -o requirements/sandbox.txt requirements/sandbox.in
	pip-compile --annotation-style=line --upgrade -o requirements/development.txt requirements/development.in
	# Handle Django via tox
	sed -i '/^[dD]jango==/d' requirements/testing.txt

quality: ## check coding style with pycodestyle and pylint
	pycodestyle codejail *.py
	isort --check-only --diff codejail *.py
	pylint codejail *.py

isort: ## apply automatic import sorting
	isort --recursive codejail *.py

requirements: dev-requirements

dev-requirements:
	pip install -r requirements/sandbox.txt
	pip install -r requirements/development.txt
