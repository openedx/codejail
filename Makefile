# Makefile for CodeJail

test.docker:
	docker build -t test-codejail -f codejail/tests/tests.dockerfile .
	docker run --cap-add SYS_RESOURCE --rm test-codejail tox
