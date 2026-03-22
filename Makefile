.PHONY: lint format build clean

lint:
	ruff check plugins/
	ruff format --check plugins/

format:
	ruff format plugins/

build:
	ansible-galaxy collection build --force

clean:
	rm -f mrekiba-bao-*.tar.gz
