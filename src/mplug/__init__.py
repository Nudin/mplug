#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

"""
MPlug – a plugin manager for mpv.

See here for details:
https://github.com/Nudin/mplug
"""

import logging
import sys
import textwrap
from typing import Optional

from .mplug import MPlug

try:
    from importlib.metadata import PackageNotFoundError, version  # type: ignore
except ImportError:  # pragma: no cover
    from importlib_metadata import PackageNotFoundError, version  # type: ignore


NAME = "mplug"
try:
    VERSION = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    VERSION = "unknown"


def print_help():
    """Print help.

    This is so far done by hand, until it's worth to use a proper argument parser."""
    help_text = f"""\
        {NAME} {VERSION}

        Usage: {NAME} [-v] command

        Available commands:
        - install NAME|ID          Install a plugin by name or plugin-id
        - uninstall NAME|ID        Remove a plugin from the system
        - disable NAME|ID          Disable a plugin without deleting it from the system
        - search TEXT              Search for a plugin by name and description
        - update                   Update the list of available plugins
        - upgrade                  Update all plugins
        - list-installed           List all plugins installed with {NAME}
        """
    print(textwrap.dedent(help_text))


logging.basicConfig(level="INFO", format="%(message)s")


def main(operation: str, name: Optional[str] = None, verbose: bool = False):
    """Load mplug and call the desired operation."""
    # Initialize mplug and load script directory
    plug = MPlug(verbose)

    if operation == "install":
        assert name is not None
        plug.install_by_name(name)
    elif operation == "uninstall":
        assert name is not None
        plug.uninstall_by_name(name)
    elif operation == "search":
        assert name is not None
        plug.search(name)
    elif operation == "disable":
        assert name is not None
        plug.uninstall_by_name(name, remove=False)
    elif operation == "update":
        plug.update()
    elif operation == "upgrade":
        plug.upgrade()
    elif operation == "list-installed":
        plug.list_installed()

    plug.save_state_to_disk()


def arg_parse(argv):
    """Parse the command line arguments."""
    if len(argv) > 1 and argv[1] == "-v":
        verbose = True
        logging.getLogger().setLevel("DEBUG")
        del argv[1]
    else:
        verbose = False
    if len(argv) < 2:
        print_help()
        sys.exit(0)
    operation = argv[1]

    if operation == "help":
        print_help()
        sys.exit(0)

    if operation not in [
        "install",
        "upgrade",
        "uninstall",
        "update",
        "disable",
        "search",
        "list-installed",
    ]:
        print_help()
        sys.exit(1)

    if operation in ["install", "uninstall", "search", "disable"]:
        if len(argv) < 3:
            print_help()
            sys.exit(2)
        else:
            name = argv[2]
    else:
        name = None
    return operation, name, verbose


def run():
    """Main entry point"""
    main(*arg_parse(sys.argv))


if __name__ == "__main__":
    run()
