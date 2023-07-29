import datetime

templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"

project = "I hate money"
year = datetime.datetime.now().strftime("%Y")
copyright = f"2011-{year}, The 'I hate money' team"

version = "5.0"
release = "5.0"
exclude_patterns = ["_build"]
pygments_style = "sphinx"
extensions = ["myst_parser", "sphinx.ext.autosectionlabel"]

myst_enable_extensions = [
    "colon_fence",
]
autosectionlabel_prefix_document = True
