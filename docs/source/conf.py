# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import re
import argparse

import docutils.nodes
import sphinx.transforms
import sphinx.application
import sphinx.util.docutils

import rez_pip.cli

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


class ReplaceGHRefs(sphinx.transforms.SphinxTransform):
    default_priority = 750
    prefix = "https://github.com/JeanChristopheMorinPerso/rez-pip/issues"

    def apply(self):
        istext = lambda o: isinstance(o, docutils.nodes.Text)

        for node in self.document.traverse(istext):
            match = re.match(r".*\((\#(\d+))\)\.?$", str(node))
            if not match:
                continue

            newtext = docutils.nodes.Text(str(node)[: match.start(1)])
            newreference = docutils.nodes.reference(
                "", match.group(1), refuri=f"{self.prefix}/{match.group(2)}"
            )
            trailingtext = docutils.nodes.Text(str(node)[match.end(1) :])
            node.parent.replace(node, newtext)
            node.parent.insert(node.parent.index(newtext) + 1, newreference)
            node.parent.insert(node.parent.index(newtext) + 2, trailingtext)

        return


class RezAutoArgparseDirective(sphinx.util.docutils.SphinxDirective):
    """
    Special rez-autoargparse directive. This is quite similar to "autosummary" in some ways.
    """

    required_arguments = 0
    optional_arguments = 0

    def run(self) -> list[docutils.nodes.Node]:
        # Create the node.
        node = docutils.nodes.section()
        node.document = self.state.document

        rst = docutils.statemachine.ViewList()

        # Add rezconfig as a dependency to the current document. The document
        # will be rebuilt if rezconfig changes.
        self.env.note_dependency(rez_pip.cli.__file__)
        self.env.note_dependency(__file__)

        path, lineNumber = self.get_source_info()

        parser = rez_pip.cli._createParser()

        full_cmd = parser.prog.replace(" ", "-")

        # Title
        document = [f".. _{full_cmd}:"]
        document.append("")
        document.append(f"{'='*len(parser.prog)}")
        document.append(f"{full_cmd}")
        document.append(f"{'='*len(parser.prog)}")
        document.append("")

        document.append(f".. program:: {full_cmd}")
        document.append("")
        document.append("Usage")
        document.append("=====")
        document.append("")
        document.append(".. code-block:: text")
        document.append("")
        for line in parser.format_usage()[7:].split("\n"):
            document.append(f"   {line}")
        document.append("")

        document.append("Description")
        document.append("===========")
        document.extend(parser.description.split("\n"))

        for group in parser._action_groups:
            if not group._group_actions:
                continue

            document.append("")
            title = group.title.capitalize()
            document.append(title)
            document.append("=" * len(title))
            document.append("")

            for action in group._group_actions:
                if isinstance(action, argparse._HelpAction):
                    continue

                # Quote default values for string/None types
                default = action.default
                if (
                    action.default not in ["", None, True, False]
                    and action.type in [None, str]
                    and isinstance(action.default, str)
                ):
                    default = f'"{default}"'

                # fill in any formatters, like %(default)s
                format_dict = dict(vars(action), prog=parser.prog, default=default)
                format_dict["default"] = default
                help_str = action.help or ""  # Ensure we don't print None
                try:
                    help_str = help_str % format_dict
                except Exception:
                    pass

                if help_str == argparse.SUPPRESS:
                    continue

                # Avoid Sphinx warnings.
                help_str = help_str.replace("*", "\\*")
                # Replace everything that looks like an argument with an option directive.
                help_str = re.sub(
                    r"(?<!\w)-[a-zA-Z](?=\s|\/|\)|\.?$)|(?<!\w)--[a-zA-Z-0-9]+(?=\s|\/|\)|\.?$)",
                    r":option:`\g<0>`",
                    help_str,
                )
                help_str = help_str.replace("--", "\\--")

                # Add links to rez docs for known settings.
                help_str = re.sub(
                    "(.* \(default: configured )([a-zA-Z_]+)(.*)$",
                    r"\g<1> :external:data:`\g<2>`\g<3>",
                    help_str,
                )

                # Options have the option_strings set, positional arguments don't
                name = action.option_strings
                if name == []:
                    if action.metavar is None:
                        name = [action.dest]
                    else:
                        name = [action.metavar]

                # Skip lines for subcommands
                if name == [argparse.SUPPRESS]:
                    continue

                metavar = action.metavar if action.metavar else ""
                document.append(f".. option:: {', '.join(name)} {metavar.lower()}")
                document.append("")
                document.append(f"   {help_str}")
                if action.choices:
                    document.append("")
                    document.append(f"   Choices: {', '.join(action.choices)}")
                document.append("")

        document = "\n".join(document)

        # Add each line to the view list.
        for index, line in enumerate(document.split("\n")):
            # Note to future people that will look at this.
            # "line" has to be a single line! It can't be a line like "this\nthat".
            rst.append(line, path, lineNumber + index)

        # Finally, convert the rst into the appropriate docutils/sphinx nodes.
        sphinx.util.nodes.nested_parse_with_titles(self.state, rst, node)

        # Return the generated nodes.
        return node.children


def setup(app: sphinx.application.Sphinx):
    app.add_directive("rez-autoargparse", RezAutoArgparseDirective)
    app.add_transform(ReplaceGHRefs)
