# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

"""
Functions to download plugins from an url.

Functions: download_file, download_tar, git_clone_or_pull, git_pull
"""

import logging
import tarfile
import tempfile
from pathlib import Path

import requests
from git import Repo  # type: ignore


def download_file(url: str, filename: Path):
    """Dowload file and save it to disk."""
    result = requests.get(url)
    with open(filename, "wb") as output_file:
        output_file.write(result.content)


def download_tar(url: str, directory: Path):
    """Download and extract a tarbar to the give directory."""
    result = requests.get(url)
    with tempfile.TemporaryFile("rb+") as tmp:
        tmp.write(result.content)
        tmp.seek(0)
        tar = tarfile.open(fileobj=tmp)
        tar.extractall(directory)


def git_clone_or_pull(repourl: str, gitdir: Path) -> Repo:
    """Clone or update a repository into a given folder."""
    if gitdir.exists():
        repo = Repo(gitdir)
        logging.debug("Repo already cloned, pull latest changes instead.")
        repo.remote().pull()
    else:
        repo = Repo.clone_from(repourl, gitdir, multi_options=["--depth 1"])
    return repo


def git_pull(gitdir: Path) -> Repo:
    """Update the git repository at the given location."""
    repo = Repo(gitdir)
    repo.remote().pull()
    return repo
