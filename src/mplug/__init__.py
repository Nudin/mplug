#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

import logging
import sys
import textwrap
from typing import Optional

from .mplug import MPlug

NAME = "mplug"
VERSION = "0.1.0"


def print_help():
    help_text = f"""\
        {NAME} {VERSION}

        Usage: {NAME} [-v] command

        Available commands:
        - install NAME|ID          Install a plugin by name or plugin-id
        - uninstall ID             Remove a plugin from the system
        - disable ID               Disable a plugin without deleting it from the system
        - search TEXT              Search for a plugin by name and description
        - update                   Update the list of available plugins
        - upgrade                  Update all plugins
        - list-installed           List all plugins installed with {NAME}
        """
    print(textwrap.dedent(help_text))


logging.basicConfig(level="INFO", format="%(message)s")


def main(operation: str, name: Optional[str] = None):
    # Initialize mplug and load script directory
    plug = MPlug()

    if operation == "install":
        plug.install_by_name(name)
    elif operation == "uninstall":
        plug.uninstall(name)
    elif operation == "search":
        plug.search(name)
    elif operation == "disable":
        plug.uninstall(name, remove=False)
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
        logging.getLogger().setLevel("DEBUG")
        del argv[1]
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
    return operation, name


def run():
    main(*arg_parse(sys.argv))


if __name__ == "__main__":
    run()
