#!/usr/bin/env python
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Copyright (C) Michael F. Schönitzer, 2020

import logging
import sys
import textwrap
from typing import Optional

from .mplug import MPlug

NAME = "mplug"
VERSION = "0.1"


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
    # Load script directory
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
