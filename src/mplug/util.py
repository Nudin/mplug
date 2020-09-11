# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

"""
Different simpler functions.

Functions: wrap, resolve_templates
"""

import platform
import shutil
import textwrap


def wrap(text, indent=0, dedent=False):
    """Wrap lines of text and optionally indent it for prettier printing."""
    term_width = shutil.get_terminal_size((80, 20)).columns
    if indent:
        indents = {
            "initial_indent": "  " * indent,
            "subsequent_indent": "  " * indent,
        }
    else:
        indents = {}
    wrapper = textwrap.TextWrapper(width=min(80, term_width), **indents)
    if dedent:
        text = textwrap.dedent(text)
    lines = [wrapper.fill(line) for line in text.splitlines()]
    return "\n".join(lines)


def resolve_templates(text: str) -> str:
    """Replace placeholders in the given url/filename.

    Supported placeholders:
    - {{os}} -> linux, windows, …
    - {{arch}} -> x86_64, x86_32, …
    - {{arch-short}} -> x64, x32
    - {{shared-lib-ext}} -> so, dll
    """
    # pylint: disable=C0103
    os = platform.system().lower()
    arch = platform.machine()
    arch_short = arch.replace("x86_", "x")
    if os == "windows":
        shared_lib_ext = "dll"
    else:
        shared_lib_ext = "so"
    text = text.replace("{{shared-lib-ext}}", shared_lib_ext)
    text = text.replace("{{os}}", os)
    text = text.replace("{{arch}}", arch)
    text = text.replace("{{arch-short}}", arch_short)
    return text
