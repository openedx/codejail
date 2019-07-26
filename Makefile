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
