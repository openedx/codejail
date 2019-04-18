# Makefile for CodeJail

test: test_no_proxy test_proxy

test_no_proxy:
	@echo "Running all tests with no proxy process"
	CODEJAIL_PROXY=0 nosetests --with-xunit --xunit-file reports/nosetests-no-proxy.xml

test_proxy:
	@echo "Running all tests with proxy process"
	CODEJAIL_PROXY=1 nosetests --with-xunit --xunit-file reports/nosetests-proxy.xml
