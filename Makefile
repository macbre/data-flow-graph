coverage_options = --include='data_flow_graph.py' --omit='test/*'

install:
	pip install -e .[dev]

test:
	py.test -vv

coverage:
	rm -f .coverage*
	rm -rf htmlcov/*
	coverage run -p -m py.test -vv
	coverage combine
	coverage html -d htmlcov $(coverage_options)
	coverage xml -i
	coverage report $(coverage_options)

lint:
	pylint data_flow_graph.py

publish:
	# run git tag -a v0.0.0 before running make publish
	python setup.py sdist upload -r pypi

.PHONY: test
