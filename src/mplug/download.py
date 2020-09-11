import logging
import tarfile
import tempfile
from pathlib import Path

import requests
from git import Repo


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
    repo = Repo(gitdir)
    repo.remote().pull()
    return repo
