# Makefile for CodeJail

clean:
	find codejail -name '*.pyc' -exec rm -f {} +
	find codejail -name '*.pyo' -exec rm -f {} +
	find codejail -name '__pycache__' -exec rm -rf {} +


test: test_no_proxy test_proxy

test_no_proxy:
	@echo "Running all tests with no proxy process"
	CODEJAIL_PROXY=0 nosetests --with-xunit --xunit-file reports/nosetests-no-proxy.xml

test_proxy:
	@echo "Running all tests with proxy process"
	CODEJAIL_PROXY=1 nosetests --with-xunit --xunit-file reports/nosetests-proxy.xml


upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	pip install -q -r requirements/pip_tools.txt
	pip-compile --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	pip-compile --upgrade -o requirements/development.txt requirements/development.in
	pip-compile --upgrade -o requirements/sandbox.txt requirements/sandbox.in
	pip-compile --upgrade -o requirements/testing.txt requirements/testing.in
	pip-compile --upgrade -o requirements/tox.txt requirements/tox.in
