# SPDX-FileCopyrightText: 2022 Contributors to the rez project
#
# SPDX-License-Identifier: Apache-2.0

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import re
import inspect
import argparse
import importlib

import docutils.nodes
import sphinx.transforms
import sphinx.util.nodes
import sphinx.application
import sphinx.ext.autodoc
import sphinx.util.docutils
import docutils.statemachine

import rez_pip.cli
import rez_pip.plugins

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "rez-pip"
copyright = "Contributors to the rez project"
author = "Rez Developers"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    # first-party extensions
    "sphinx.ext.todo",
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
    r"https://github.com/JeanChristopheMorinPerso/rez-pip/issues/\d+": r"https://github.com/JeanChristopheMorinPerso/rez-pip/pull/\d+"
}


# -- Options for sphinx.ext.intersphinx_mapping ------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "rez": ("https://rez.readthedocs.io/en/stable/", None),
}

# Force usage of :external:
# intersphinx_disabled_reftypes = ["*"]


# -- Options for sphinx.ext.autodoc ------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

# autodoc_typehints = "description"
autodoc_typehints_format = "short"
autodoc_member_order = "bysource"

# -- Options for sphinx.ext.todo --------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/todo.html

todo_include_todos = True

# -- Custom ------------------------------------------------------------------
# Custom stuff


class ReplaceGHRefs(sphinx.transforms.SphinxTransform):
    default_priority = 750
    prefix = "https://github.com/JeanChristopheMorinPerso/rez-pip/issues"

    def apply(self):
        istext = lambda o: isinstance(o, docutils.nodes.Text)

        for node in self.document.traverse(istext):
            # Handle issue/PR references like (#123)
            match = re.match(r".*\((\#(\d+))\)\.?$", str(node))
            if match:
                newtext = docutils.nodes.Text(str(node)[: match.start(1)])
                newreference = docutils.nodes.reference(
                    "", match.group(1), refuri=f"{self.prefix}/{match.group(2)}"
                )
                trailingtext = docutils.nodes.Text(str(node)[match.end(1) :])
                node.parent.replace(node, newtext)
                node.parent.insert(node.parent.index(newtext) + 1, newreference)
                node.parent.insert(node.parent.index(newtext) + 2, trailingtext)
                continue

            # Handle user tags like @username
            match = re.search(r"(@([a-zA-Z0-9-]+(?:\[bot\])?))", str(node))
            if match:
                newtext = docutils.nodes.Text(str(node)[: match.start(1)])
                newreference = docutils.nodes.reference(
                    "", match.group(1), refuri=f"https://github.com/{match.group(2)}"
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

        full_cmd = parser.prog.replace(" ", "-").replace("rez-pip", "rez pip2")

        # Title
        document = [f".. _{full_cmd}:"]
        document.append("")
        document.append(f"{'='*len(full_cmd)}")
        document.append(f"{full_cmd}")
        document.append(f"{'='*len(full_cmd)}")
        document.append("")

        document.append(f".. program:: {full_cmd}")
        document.append("")
        document.append("Usage")
        document.append("=====")
        document.append("")
        document.append(".. code-block:: text")
        document.append("")
        for line in parser.format_usage()[7:].split("\n"):
            # TODO: This replace is dirty... How could we more cleany
            # get the rez pip command as a plugin?
            document.append(f"   {line}".replace("rez-pip", "rez pip2"))
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
                    r"(.* \(default: configured )([a-zA-Z_]+)(.*)$",
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


class RezAutoPlugins(sphinx.util.docutils.SphinxDirective):
    """
    Special rez-pip-autoplugins directive. This is quite similar to "autosummary" in some ways.
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
        self.env.note_dependency(rez_pip.plugins.__file__)
        self.env.note_dependency(__file__)

        path, lineNumber = self.get_source_info()

        document = []
        for plugin, hooks in rez_pip.plugins._getHookImplementations().items():
            hooks = [f":func:`{hook}`" for hook in hooks]
            document.append(f"* {plugin.split('.')[-1]}: {', '.join(hooks)}")

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


class RezPipAutoPluginHooks(sphinx.util.docutils.SphinxDirective):
    """
    Special rez-pip-autopluginhooks directive. This is quite similar to "autosummary" in some ways.
    """

    required_arguments = 1
    optional_arguments = 0

    def run(self) -> list[docutils.nodes.Node]:
        # Create the node.
        node = docutils.nodes.section()
        node.document = self.state.document

        rst = docutils.statemachine.ViewList()

        # Add rezconfig as a dependency to the current document. The document
        # will be rebuilt if rezconfig changes.
        self.env.note_dependency(rez_pip.plugins.__file__)
        self.env.note_dependency(__file__)

        path, lineNumber = self.get_source_info()

        fullyQualifiedClassName = self.arguments[0]
        module, klassname = fullyQualifiedClassName.rsplit(".", 1)

        mod = importlib.import_module(module)
        klass = getattr(mod, klassname)

        methods = [
            method
            for method in inspect.getmembers(klass, predicate=inspect.isfunction)
            if not method[0].startswith("_")
        ]

        document = []
        for method in sorted(methods, key=lambda x: x[1].__code__.co_firstlineno):
            document.append(f".. autohook:: {module}.{klassname}.{method[0]}")

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


def autodoc_process_signature(
    app: sphinx.application.Sphinx,
    what: str,
    name: str,
    obj,
    options: dict,
    signature: str,
    return_annotation,
):
    signature = signature.replace(
        "rez_pip.compat.importlib_metadata", "~importlib.metadata"
    )

    return signature, return_annotation


class HookDocumenter(sphinx.ext.autodoc.FunctionDocumenter):
    """
    Custom autohook directive to document our hooks.
    It allows us to easily document the hooks from the rez_pip.plugins.PluginSpec
    class without exposing the class and module name.
    """

    objtype = "hook"  # auto + hook
    directivetype = "function"  # generated reST directive

    def format_signature(self, **kwargs) -> str:
        """
        Format the signature and remove self. We really don't want to expose
        the class and module name or the fact that we are documenting methods.
        """
        sig = super().format_signature(**kwargs)
        sig = re.sub(r"\(self(,\s)?", "(", sig)

        # Also force short names for our own types
        sig = sig.replace("rez_pip.", "~rez_pip.")

        return sig

    def add_directive_header(self, sig):
        modname = self.modname
        # Hacky, but it does the job. This should remove the module name from the directive
        # created by autodoc.
        self.modname = ""

        data = super().add_directive_header(sig)

        # We need to restore it because autodoc does lots of things with the module name.
        self.modname = modname
        return data


def setup(app: sphinx.application.Sphinx):
    app.add_directive("rez-autoargparse", RezAutoArgparseDirective)
    app.add_directive("rez-pip-autoplugins", RezAutoPlugins)
    app.add_directive("rez-pip-autopluginhooks", RezPipAutoPluginHooks)
    app.add_transform(ReplaceGHRefs)

    app.connect("autodoc-process-signature", autodoc_process_signature)
    app.add_autodocumenter(HookDocumenter)
