# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

"""
Different simpler functions.

Functions: wrap, resolve_templates
"""

import os
import platform
import re
import shutil
import stat
import textwrap
from pathlib import Path
from typing import List


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
    - {{shared-lib-ext}} -> .so, .dll
    - {{executable-ext}} -> .exe or nothing, if later remove dot
    """
    # pylint: disable=C0103
    os_name = platform.system().lower()
    arch = platform.machine()
    arch_short = arch.replace("x86_", "x")
    if os_name == "windows":
        shared_lib_ext = r"\1dll"
        executable_ext = r"\1exe"
    else:
        shared_lib_ext = r"\1so"
        executable_ext = ""
    text = re.sub(r"(\.?){{shared-lib-ext}}", shared_lib_ext, text)
    text = re.sub(r"(\.?){{executable-ext}}", executable_ext, text)
    text = text.replace("{{os}}", os_name)
    text = text.replace("{{arch}}", arch)
    text = text.replace("{{arch-short}}", arch_short)
    return text


def make_files_executable(filelist: List[Path]):
    """On *nix based operating systems, mark the file as executable."""
    os_name = platform.system().lower()
    if "windows" in os_name:
        return
    for file in filelist:
        st = os.stat(file)
        os.chmod(file, st.st_mode | stat.S_IEXEC)
