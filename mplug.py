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


import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from git import Repo


def ask_num(question: str, options: List[str]) -> Optional[str]:
    """Ask to choose from a number of options.

    The user is given a list of numbered options and should pick one, by
    entering the corresponding number.

    question: The message that is shown to the user
    options: The options from which the user should pick
    returns: the choice
    """
    print(question)
    for i, opt in enumerate(options):
        print(f"[i] {opt}")
    answer = input("> ")
    try:
        num = int(answer)
        assert num >= 0
        assert num < len(options)
        return options[num]
    except ValueError:
        return None
    except AssertionError:
        return None


def ask_yes_no(question: str) -> bool:
    """Ask a yes-no-question."""
    answer = input(f"{question} [y/N] ")
    if answer in ["y", "Y"]:
        return True
    return False


class MPlug:
    """Plugin Manager for mpv.

    MPlug can install, update and uninstall scripts, shaders, or other tools to
    enhance the video player mpv. It is based on the `mpv script directory`,
    that ideally contains all known scripts with machine readable metadata to
    install them. The git repository of the script directory is cloned into a
    subdirectory of the working directory and updated by hand (update()) or
    after 30 days.

    When installing a plugin it is downloaded (usually via git) into a
    subdirectory of the working directory. Symbolic Links to the scrip files
    are then created in the folders that mpv expects them to be. This way
    plugins can be easily disabled or updated and the directories stay clear
    and uncluttered.
    """

    directory_foldername = "mpv_script_dir"
    directory_filename = "mpv_script_directory.json"
    directory_remoteurl = "https://github.com/Nudin/mpv-script-directory.git"

    def __init__(self):
        """Initialise Plugin Manager.

        Clone the script directory if not already available, update it if it
        hasn't been updated since more then 30 days. Then read the directory.
        """
        self.__get_dirs__()
        script_dir_file = self.directory_folder / self.directory_filename
        if not self.directory_folder.exists():
            self.update()
        else:
            age = datetime.now().timestamp() - script_dir_file.stat().st_mtime
            if age > 60 * 60 * 24 * 30:
                self.update()
        with open(script_dir_file) as f:
            self.script_directory = json.load(f)

    def update(self):
        """Get or update the 'mpv script directory'."""
        print(f"Updating {self.directory_filename}")
        self.__clone_git__(self.directory_remoteurl, self.directory_folder)

    def uninstall(self, script_id: str, remove: bool = True):
        """Remove or disable a script.

        remove: if True the tools folder will be deleted from disc. If False
        only remove the symlinks to the files.
        """
        if script_id not in self.script_directory:
            print("Not installed")
            exit(10)
            return False
        script = self.script_directory[script_id]
        if "install" not in script:
            print(f"No installation method for {script_id}")
            exit(4)
        elif script["install"] == "git":
            gitdir = self.workdir / script["gitdir"]
            print(f"Remove directory {gitdir}")
            if remove:
                shutil.rmtree(gitdir)
            scriptfiles = script.get("scriptfiles", [])
            self.__uninstall_files__(scriptfiles)
        else:
            print(
                f"Can't install {script_id}: unknown installation method: {script['install']}"
            )
            exit(5)

    def install_by_name(self, name: str):
        """Install a script with the given name or id.

        If there are multiple scripts with the same name the user is asked to
        choose."""
        if name in self.script_directory:
            return self.install(name)
        else:
            scripts = []
            for key, value in self.script_directory.items():
                if value["name"] == name:
                    scripts.append(key)
            return self.install_from_list(scripts)

    def search(self, seach_string: str):
        """Search names and descriptions of scripts."""
        scripts = []
        for key, value in self.script_directory.items():
            if seach_string in value["name"]:
                scripts.append(key)
            elif seach_string in value["desc"]:
                scripts.append(key)
        self.install_from_list(scripts)

    def install_from_list(self, scripts: List[str]):
        """Ask the user which of the scripts should be installed."""
        if len(scripts) == 0:
            print(f"Script {name} not known")
            exit(3)
        elif len(scripts) == 1:
            if ask_yes_no(f"Install {scripts[0]}?"):
                self.install(scripts[0])
            else:
                exit(0)
        else:
            choise = ask_num("Found multiple scripts:", scripts)
            if choise:
                self.install(choise)
            else:
                exit(0)

    def install(self, script_id: str):
        """Install the script with the given script id."""
        script = self.script_directory[script_id]

        if "install" not in script:
            print(f"No installation method for {script_id}")
            exit(4)
        elif script["install"] == "git":
            gitdir = self.workdir / script["gitdir"]
            repourl = script["git"]
            scriptfiles = script.get("scriptfiles", [])
            self.__clone_git__(repourl, gitdir)
            self.__install_files__(gitdir, scriptfiles)
        else:
            print(
                f"Can't install {script_id}: unknown installation method: {script['install']}"
            )
            exit(5)

    def upgrade(self):
        """Upgrade all repositories in the working directory."""
        for gitdir in self.workdir.glob("*/*"):
            repo = Repo(gitdir)
            repo.remote().pull()

    def __get_dirs__(self):
        """Find the directory paths by using XDG environment variables or
        hardcoded fallbacks. Create working directory if it does not exist."""
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            self.workdir = Path(xdg_data) / "mplug"
        else:
            self.workdir = Path.home() / ".mplug"
        xdg_conf = os.environ.get("XDG_CONFIG_HOME")
        if xdg_conf:
            self.scriptdir = Path(xdg_conf) / "mpv" / "scripts"
            self.shaderdir = Path(xdg_conf) / "mpv" / "shaders"
        else:
            self.scriptdir = Path.home() / ".config" / "mpv" / "scripts"
            self.shaderdir = Path.home() / ".config" / "mpv" / "shaders"
        if not self.workdir.exists():
            os.mkdir(self.workdir)
        self.directory_folder = self.workdir / self.directory_foldername

    def __clone_git__(self, repourl: str, gitdir: Path) -> Repo:
        """Clone or update a repository into a given folder."""
        if gitdir.exists():
            repo = Repo(gitdir)
            repo.remote().pull()
        else:
            repo = Repo.clone_from(repourl, gitdir)
        return repo

    def __install_files__(self, srcdir: Path, scriptfiles: List[str]):
        """Install all scriptfiles as symlinks into the corresponding folder."""
        if not self.scriptdir.exists():
            os.mkdir(self.scriptdir)
        for file in scriptfiles:
            src = srcdir / file
            dst = self.scriptdir / file
            if dst.exists():
                print("File already exists:", dst)
                continue
            os.symlink(src, dst)

    def __uninstall_files__(self, scriptfiles: List[str]):
        """Remove symlinks."""
        for file in scriptfiles:
            dst = self.scriptdir / file
            print(f"Removing {dst}")
            os.remove(dst)


if __name__ == "__main__":  # noqa: C901
    if len(sys.argv) < 2:
        exit(0)
    operation = sys.argv[1]

    if operation not in [
        "install",
        "upgrade",
        "uninstall",
        "update",
        "disable",
        "search",
    ]:
        exit(1)

    if operation in ["install", "uninstall", "search", "disable"] and len(sys.argv) < 3:
        exit(2)

    # Load script directory
    plug = MPlug()

    if operation == "install":
        name = sys.argv[2]
        plug.install_by_name(name)
    elif operation == "uninstall":
        name = sys.argv[2]
        plug.uninstall(name)
    elif operation == "search":
        name = sys.argv[2]
        plug.search(name)
    elif operation == "disable":
        name = sys.argv[2]
        plug.uninstall(name, remove=False)
    elif operation == "update":
        plug.update()
    elif operation == "upgrade":
        plug.upgrade()
