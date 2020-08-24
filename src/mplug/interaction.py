# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

import itertools
import shutil
import textwrap
from pathlib import Path
from typing import List, Optional


def ask_num(
    question: str, options: List[str], descriptions: Optional[List[str]] = None
) -> Optional[str]:
    """Ask to choose from a number of options.

    The user is given a list of numbered options and should pick one, by
    entering the corresponding number.

    question: The message that is shown to the user
    options: The options from which the user should pick
    descriptions: Array of strings, same length as options. Description for the
    options that will be printed together with the options.
    returns: the choice
    """
    if descriptions is None:
        descriptions = itertools.repeat(None)
    term_width = shutil.get_terminal_size((80, 20)).columns
    wrapper = textwrap.TextWrapper(
        width=min(100, term_width), initial_indent="  ", subsequent_indent="  "
    )
    print(question)
    for i, (opt, desc) in enumerate(zip(options, descriptions)):
        print(f"[{i}] {opt}")
        if desc is not None:
            print(wrapper.fill(desc))
    try:
        answer = input("> ")
        num = int(answer)
        assert num >= 0
        assert num < len(options)
        return options[num]
    except ValueError:
        return None
    except AssertionError:
        return None
    except KeyboardInterrupt:
        print()
        return None
    except EOFError:
        print()
        return None


def ask_yes_no(question: str) -> bool:
    """Ask a yes-no-question."""
    answer = input(f"{question} [y/N] ")
    if answer in ["y", "Y"]:
        return True
    return False


def ask_path(question: str, default: Path) -> Path:
    """Ask the user for a file path, with a fallback if the user does not enter
    anything.

    question: Text to display on promt
    default: Default path, returned if user gives no input"""
    pathstr = input(f"{question} [{default}]\n> ").strip()
    if pathstr == "":
        path = default
    else:
        path = Path(pathstr)
    return path.expanduser().absolute()
