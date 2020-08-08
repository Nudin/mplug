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
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from git import Repo

NAME = "mplug"
VERSION = "0.1"


def print_help():
    print(
        f"""{NAME} {VERSION}

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
    )


logging.basicConfig(level="INFO", format="%(message)s")


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
        print(f"[{i}] {opt}")
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
    and uncluttered. A file is used to keep a list of all installed plugins.
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
                logging.debug("Update mpv_script_directory due to it's age")
                self.update()
        with open(script_dir_file) as f:
            self.script_directory = json.load(f)
        self.statefile = self.workdir / "installed_plugins"
        try:
            with open(self.statefile) as f:
                self.installed_scripts = json.load(f)
        except json.JSONDecodeError as e:
            logging.error("Failed to load mplug file %s: %e", self.statefile, e)
            exit(11)
        except FileNotFoundError:
            logging.debug("No packages installed yet.")
            self.installed_scripts = {}

    def __del__(self):
        """Write installed plugins on exit."""
        try:
            with open(self.statefile, "w") as f:
                json.dump(self.installed_scripts, f)
                logging.debug("Saving list of installed scripts")
        except Exception:
            # If an error occurs the interpreter will shutdown before calling del
            pass

    def update(self):
        """Get or update the 'mpv script directory'."""
        logging.info(f"Updating {self.directory_filename}")
        self.__clone_git__(self.directory_remoteurl, self.directory_folder)

    def uninstall(self, script_id: str, remove: bool = True):
        """Remove or disable a script.

        remove: if True the tools folder will be deleted from disc. If False
        only remove the symlinks to the files.
        """
        if script_id not in self.installed_scripts:
            logging.error("Not installed")
            exit(10)
            return False
        script = self.installed_scripts[script_id]
        if "install" not in script:
            logging.error(f"No installation method for {script_id}")
            exit(4)
        elif script["install"] == "git":
            logging.debug("Remove links of {script_id}")
            gitdir = self.workdir / script["gitdir"]
            scriptfiles = script.get("scriptfiles", [])
            shaderfiles = script.get("shaderfiles", [])
            fontfiles = script.get("fontfiles", [])
            scriptoptfiles = script.get("scriptoptfiles", [])
            exefiles = script.get("exefiles", [])
            exedir = script.get("exedir")
            self.__uninstall_files__(scriptfiles, self.scriptdir)
            self.__uninstall_files__(scriptoptfiles, self.scriptoptsdir)
            self.__uninstall_files__(fontfiles, self.fontsdir)
            self.__uninstall_files__(shaderfiles, self.shaderdir)
            if exefiles:
                if exedir:
                    logging.debug("Remove link to executables in %s", exedir)
                    self.__uninstall_files__(exefiles, exedir)
                else:
                    logging.error(
                        "Can't uninstall files %s: unknown location.", exefiles
                    )
            if remove:
                logging.info(f"Remove directory {gitdir}")
                shutil.rmtree(gitdir)
        else:
            logging.error(
                f"Can't install {script_id}: unknown installation method: {script['install']}"
            )
            exit(5)
        del self.installed_scripts[script_id]

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
        seach_string = seach_string.lower()
        for key, value in self.script_directory.items():
            if seach_string in value.get("name", ""):
                scripts.append(key)
            elif seach_string in value.get("desc", "").lower():
                scripts.append(key)
        self.install_from_list(scripts)

    def install_from_list(self, scripts: List[str]):
        """Ask the user which of the scripts should be installed."""
        logging.debug("Found %i potential scripts", len(scripts))
        if len(scripts) == 0:
            logging.error(f"Script {name} not known")
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
        script = self.script_directory[script_id].copy()

        if "install" not in script:
            logging.error(f"No installation method for {script_id}")
            exit(4)
        elif script["install"] == "git":
            gitdir = self.workdir / script["gitdir"]
            repourl = script["git"]
            scriptfiles = script.get("scriptfiles", [])
            shaderfiles = script.get("shaderfiles", [])
            fontfiles = script.get("fontfiles", [])
            scriptoptfiles = script.get("scriptoptfiles", [])
            exefiles = script.get("exefiles", [])
            logging.debug("Clone git repo %s to %s", repourl, gitdir)
            self.__clone_git__(repourl, gitdir)
            self.__install_files__(
                srcdir=gitdir, filelist=scriptfiles, dstdir=self.scriptdir
            )
            self.__install_files__(
                srcdir=gitdir, filelist=shaderfiles, dstdir=self.shaderdir
            )
            self.__install_files__(
                srcdir=gitdir, filelist=fontfiles, dstdir=self.fontsdir
            )
            self.__install_files__(
                srcdir=gitdir, filelist=scriptoptfiles, dstdir=self.scriptoptsdir
            )
            if exefiles:
                pathstr = input("Where to put executable files? [~/bin]\n> ").strip()
                if pathstr == "":
                    exedir = Path.home() / "bin"
                else:
                    exedir = Path(pathstr).expanduser().absolute()
                logging.info("Placing executables in %s", str(exedir))
                self.__install_files__(srcdir=gitdir, filelist=exefiles, dstdir=exedir)
                script["execdir"] = str(exedir)

        else:
            logging.error(
                f"Can't install {script_id}: unknown installation method: {script['install']}"
            )
            exit(5)
        if "install-notes" in script:
            print(" " + script["install-notes"].replace("\n", "\n "))
        script["install_date"] = datetime.now().isoformat()
        self.installed_scripts[script_id] = script

    def upgrade(self):
        """Upgrade all repositories in the working directory."""
        for gitdir in self.workdir.glob("*/*"):
            logging.info("Updating repo in %s", gitdir)
            repo = Repo(gitdir)
            repo.remote().pull()

    def list_installed(self):
        """List all installed scripts"""
        logging.debug("%i installed scripts", len(self.installed_scripts))
        print("\n".join(self.installed_scripts.keys()))

    def __get_dirs__(self):
        """Find the directory paths by using XDG environment variables or
        hardcoded fallbacks. Create working directory if it does not exist."""
        xdg_data = os.getenv("XDG_DATA_HOME")
        xdg_conf = os.getenv("XDG_CONFIG_HOME")
        appdata = os.getenv("APPDATA")
        mpv_home = os.getenv("MPV_HOME")
        # Directory for MPlug this is where all script files will be stored
        if xdg_data:
            self.workdir = Path(xdg_data) / "mplug"
        elif appdata:
            self.mpvdir = Path(appdata) / "mplug"
        else:
            self.workdir = Path.home() / ".mplug"
        # MPV directory usually ~/.config/mpv on Linux/Mac
        if mpv_home:
            self.mpvdir = Path(mpv_home)
        elif xdg_conf:
            self.mpvdir = Path(xdg_conf) / "mpv"
        elif appdata:
            self.mpvdir = Path(appdata) / "mpv"
        else:
            self.mpvdir = Path.home() / ".mpv"
            logging.info(
                "No environment variable found, guessing %s as mpv config folder.",
                self.mpvdir,
            )
        logging.debug("mpvdir: %s", self.mpvdir)
        self.scriptdir = self.mpvdir / "scripts"
        self.shaderdir = self.mpvdir / "shaders"
        self.scriptoptsdir = self.mpvdir / "script-opts"
        self.fontsdir = self.mpvdir / "fonts"
        if not self.workdir.exists():
            logging.DEBUG("Create workdir %s", self.workdir)
            os.makedirs(self.workdir)
        self.directory_folder = self.workdir / self.directory_foldername

    def __clone_git__(self, repourl: str, gitdir: Path) -> Repo:
        """Clone or update a repository into a given folder."""
        if gitdir.exists():
            repo = Repo(gitdir)
            logging.debug("Repo already cloned, pull latest changes instead.")
            repo.remote().pull()
        else:
            repo = Repo.clone_from(repourl, gitdir)
        return repo

    def __install_files__(self, srcdir: Path, filelist: List[str], dstdir: Path):
        """Install all scriptfiles as symlinks into the corresponding folder."""
        if not dstdir.exists():
            logging.debug("Create directory %s", dstdir)
            os.makedirs(dstdir)
        for file in filelist:
            src = srcdir / file
            filename = Path(file).name
            dst = dstdir / filename
            if dst.exists():
                logging.info("File already exists: %s", dst)
                continue
            logging.debug("Copying file %s to %s", filename, dst)
            os.symlink(src, dst)

    def __uninstall_files__(self, filelist: List[str], folder: Path):
        """Remove symlinks."""
        for file in filelist:
            filename = Path(file).name
            dst = folder / filename
            logging.info(f"Removing {dst}")
            if not dst.is_symlink:
                logging.critical(
                    "File %s is not a symlink! It apparently was not installed by %s. Aborting.",
                    dst,
                    NAME,
                )
                exit(12)
            os.remove(dst)


if __name__ == "__main__":  # noqa: C901
    if len(sys.argv) > 1 and sys.argv[1] == "-v":
        logging.getLogger().setLevel("DEBUG")
        del sys.argv[1]
    if len(sys.argv) < 2:
        print_help()
        exit(0)
    operation = sys.argv[1]

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
        exit(1)

    if operation in ["install", "uninstall", "search", "disable"] and len(sys.argv) < 3:
        print_help()
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
    elif operation == "list-installed":
        plug.list_installed()
    else:
        print_help()

    # Necessary since otherwise will be deleted in shutdown, where open is not
    # available anymore.
    del plug
