.PHONY: black clean db

develop: venv dev-venv
dev-venv: .dev-venv
.dev-venv:
	. venv/bin/activate; \
	pip install -r dev-requirements.txt
	touch .dev-venv

install: venv db

bootstrap: db
db: venv
	. venv/bin/activate; \
	python -c 'from api import db; db.create_all()'

venv:
	virtualenv -p python3 venv
	. venv/bin/activate; \
	pip install -r requirements.txt

black: dev-venv
	. venv/bin/activate; \
	black .

clean:
	rm -rf venv
	rm .dev-venv

