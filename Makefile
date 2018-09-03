VIRTUALENV = virtualenv --python=python3
SPHINX_BUILDDIR = docs/_build
VENV := $(shell realpath $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python3
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
DOC_STAMP = $(VENV)/.doc_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -d)

.PHONY: all
all: install ## Alias for install
.PHONY: install
install: virtualenv $(INSTALL_STAMP) ## Install dependencies
$(INSTALL_STAMP):
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt
	touch $(INSTALL_STAMP)

.PHONY: virtualenv
virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)

.PHONY: install-dev
install-dev: $(INSTALL_STAMP) $(DEV_STAMP) ## Install development dependencies
$(DEV_STAMP): $(PYTHON) dev-requirements.txt
	$(VENV)/bin/pip install -Ur dev-requirements.txt
	touch $(DEV_STAMP)

.PHONY: remove-install-stamp
remove-install-stamp:
	rm $(INSTALL_STAMP)

.PHONY: update
update: remove-install-stamp install ## Update the dependencies

.PHONY: serve
serve: install ## Run the ihatemoney server
	@echo 'Running ihatemoney on http://localhost:5000'
	$(PYTHON) -m ihatemoney.manage runserver

.PHONY: test
test: $(DEV_STAMP) ## Run the tests
	$(VENV)/bin/tox

.PHONY: release
release: $(DEV_STAMP) ## Release a new version (see https://ihatemoney.readthedocs.io/en/latest/contributing.html#how-to-release)
	$(VENV)/bin/fullrelease

.PHONY: build-translations
build-translations: ## Build the translations
	$(VENV)/bin/pybabel compile -d ihatemoney/translations

.PHONY: update-translations
update-translations: ## Extract new translations from source code
	$(VENV)/bin/pybabel extract --strip-comments --omit-header --no-location --mapping-file ihatemoney/babel.cfg -o ihatemoney/messages.pot ihatemoney
	$(VENV)/bin/pybabel update -i ihatemoney/messages.pot -d ihatemoney/translations/

.PHONY: create-database-revision
create-database-revision: ## Create a new database revision
	@read -p "Please enter a message describing this revision: " rev_message; \
	$(PYTHON) -m ihatemoney.manage db migrate -d ihatemoney/migrations -m "$${rev_message}"

.PHONY: build-requirements
build-requirements: ## Save currently installed packages to requirements.txt
	$(VIRTUALENV) $(TEMPDIR)
	$(TEMPDIR)/bin/pip install -U pip
	$(TEMPDIR)/bin/pip install -Ue "."
	$(TEMPDIR)/bin/pip freeze | grep -v -- '-e' > requirements.txt

.PHONY: clean
clean: ## Destroy the virtual environment
	rm -rf .venv

.PHONY: help
help: ## Show the help indications
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
