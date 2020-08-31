import platform
import shutil
import tarfile
import tempfile
import textwrap
from pathlib import Path

import requests


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


def download_file(url: str, filename: Path):
    """Dowload file and save it to disk."""
    r = requests.get(url)
    with open(filename, "wb") as f:
        f.write(r.content)


def download_tar(url: str, directory: Path):
    """Download and extract a tarbar to the give directory."""
    r = requests.get(url)
    with tempfile.TemporaryFile("rb+") as tmp:
        tmp.write(r.content)
        tmp.seek(0)
        tar = tarfile.TarFile(fileobj=tmp)
        tar.extractall(directory)

def resolve_templates(text: str) -> str:
    """Replace placeholders in the given url/filename.

    Supported placeholders:
    - {{os}} -> linux, windows, …
    - {{arch}} -> x86_64, x86_32, …
    - {{arch-short}} -> x64, x32
    - {{shared-lib-ext}} -> so, dll
    """
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
