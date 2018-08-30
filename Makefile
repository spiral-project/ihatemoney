VIRTUALENV = virtualenv --python=python3
SPHINX_BUILDDIR = docs/_build
VENV := $(shell realpath $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python3
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
DOC_STAMP = $(VENV)/.doc_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -d)

all: install ## Alias for install
install: virtualenv $(INSTALL_STAMP) ## Install dependencies
$(INSTALL_STAMP):
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt
	touch $(INSTALL_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)

install-dev: $(INSTALL_STAMP) $(DEV_STAMP) ## Install development dependencies
$(DEV_STAMP): $(PYTHON) dev-requirements.txt
	$(VENV)/bin/pip install -Ur dev-requirements.txt
	touch $(DEV_STAMP)

remove-install-stamp:
	rm $(INSTALL_STAMP)

update: remove-install-stamp install ## Update the dependencies

serve: install ## Run the ihatemoney server
	$(PYTHON) -m ihatemoney.manage runserver

test: $(DEV_STAMP) ## Run the tests
	$(VENV)/bin/tox

release: $(DEV_STAMP) ## Release a new version (see https://ihatemoney.readthedocs.io/en/latest/contributing.html#how-to-release)
	$(VENV)/bin/fullrelease

build-translations: ## Build the translations
	$(VENV)/bin/pybabel compile -d ihatemoney/translations

update-translations: ## Extract new translations from source code
	$(VENV)/bin/pybabel extract --strip-comments --omit-header --no-location --mapping-file ihatemoney/babel.cfg -o ihatemoney/messages.pot ihatemoney
	$(VENV)/bin/pybabel update -i ihatemoney/messages.pot -d ihatemoney/translations/

create-database-revision: ## Create a new database revision
	@read -p "Please enter a message describing this revision: " rev_message; \
	$(PYTHON) -m ihatemoney.manage db migrate -d ihatemoney/migrations -m "$${rev_message}"

build-requirements: ## Save currently installed packages to requirements.txt
	$(VIRTUALENV) $(TEMPDIR)
	$(TEMPDIR)/bin/pip install -U pip
	$(TEMPDIR)/bin/pip install -Ue "."
	$(TEMPDIR)/bin/pip freeze | grep -v -- '-e' > requirements.txt

clean: ## Destroy the virtual environment
	rm -rf .venv

help: ## Show the help indications
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
