# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from sphinx.application import Sphinx
from sphinx.transforms import SphinxTransform
from docutils.nodes import reference, Text
import re

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "rez-pip"
copyright = "Contributors to the rez project"
author = "Rez Developers"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    # first-party extensions
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    # Third-part
    "sphinx_inline_tabs",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]


# -- Options for sphinx.ext.autosectionlabel ---------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autosectionlabel.html

autosectionlabel_prefix_document = True


# -- Options for the linkcheck builder ---------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-the-linkcheck-builder

linkcheck_allowed_redirects = {
    r"https://github.com/JeanChristopheMorinPerso/rez-pip/issues/\d+": "https://github.com/JeanChristopheMorinPerso/rez-pip/pull/\d+"
}


# -- Options for sphinx.ext.intersphinx_mapping ------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

intersphinx_mapping = {
    "rez": ("https://rez.readthedocs.io/en/stable/", None),
}

# Force usage of :external:
intersphinx_disabled_reftypes = ["*"]


# -- Custom ------------------------------------------------------------------
# Custom stuff


class ReplaceGHRefs(SphinxTransform):
    default_priority = 750
    prefix = "https://github.com/JeanChristopheMorinPerso/rez-pip/issues"

    def apply(self):
        istext = lambda o: isinstance(o, Text)

        for node in self.document.traverse(istext):
            match = re.match(r".*\((\#(\d+))\)\.?$", str(node))
            if not match:
                continue

            newtext = Text(str(node)[: match.start(1)])
            newreference = reference(
                "", match.group(1), refuri=f"{self.prefix}/{match.group(2)}"
            )
            trailingtext = Text(str(node)[match.end(1) :])
            node.parent.replace(node, newtext)
            node.parent.insert(node.parent.index(newtext) + 1, newreference)
            node.parent.insert(node.parent.index(newtext) + 2, trailingtext)

        return


def setup(app: Sphinx):
    app.add_transform(ReplaceGHRefs)
