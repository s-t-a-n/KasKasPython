"""Sphinx configuration."""
project = "Nomad"
author = "Stan Verschuuren"
copyright = "2022, Stan Verschuuren"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser",
]
autodoc_typehints = "description"
html_theme = "furo"
