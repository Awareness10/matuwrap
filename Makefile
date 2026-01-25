.PHONY: test coverage coverage-html build dev clean

test:
	uv run python -m unittest discover -s tests -v

coverage:
	uv run coverage run -m unittest discover -s tests
	uv run coverage report -m

coverage-html:
	uv run coverage run -m unittest discover -s tests
	uv run coverage html
	xdg-open htmlcov/index.html

build:
	uv run maturin build --release
	uv tool install .

dev:
	uv run maturin develop --release

clean:
	rm -rf build/ dist/ *.egg-info htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
