# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

import json
import logging
import os
import shutil
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from git import Repo

from .interaction import ask_num, ask_path, ask_yes_no

NAME = "mplug"
VERSION = "0.1"


class MPlug:
    """Plugin Manager for mpv.

    MPlug can install, update and uninstall plugins, shaders, or other tools to
    enhance the video player mpv. It is based on the `mpv script directory`,
    that ideally contains all known plugins with machine readable metadata to
    install them. The git repository of the plugin directory is cloned into a
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
        if not self.workdir.exists():
            logging.debug("Create workdir %s", self.workdir)
            os.makedirs(self.workdir)
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
                self.installed_plugins = json.load(f)
        except json.JSONDecodeError as e:
            logging.error("Failed to load mplug file %s: %s", self.statefile, e)
            sys.exit(11)
        except FileNotFoundError:
            logging.debug("No packages installed yet.")
            self.installed_plugins = {}

    def save_state_to_disk(self):
        """Write installed plugins on exit."""
        with open(self.statefile, "w") as f:
            json.dump(self.installed_plugins, f)
            logging.debug("Saving list of installed plugins")

    def update(self):
        """Get or update the 'mpv script directory'."""
        logging.info(f"Updating {self.directory_filename}")
        self.__clone_git__(self.directory_remoteurl, self.directory_folder)

    def uninstall(self, plugin_id: str, remove: bool = True):
        """Remove or disable a plugin.

        remove: if True the tools folder will be deleted from disc. If False
        only remove the symlinks to the files.
        """
        if plugin_id not in self.installed_plugins:
            logging.error("Not installed")
            sys.exit(10)
        plugin = self.installed_plugins[plugin_id]
        if "install" not in plugin:
            logging.error(f"No installation method for {plugin_id}")
            sys.exit(4)
        elif plugin["install"] == "git":
            logging.debug("Remove links of {plugin_id}")
            gitdir = self.workdir / plugin["gitdir"]
            scriptfiles = plugin.get("scriptfiles", [])
            shaderfiles = plugin.get("shaderfiles", [])
            fontfiles = plugin.get("fontfiles", [])
            scriptoptfiles = plugin.get("scriptoptfiles", [])
            exefiles = plugin.get("exefiles", [])
            exedir = plugin.get("exedir")
            self.__uninstall_files__(scriptfiles, self.scriptdir)
            self.__uninstall_files__(scriptoptfiles, self.scriptoptsdir)
            self.__uninstall_files__(fontfiles, self.fontsdir)
            self.__uninstall_files__(shaderfiles, self.shaderdir)
            if exefiles:
                if exedir:
                    logging.debug("Remove link to executables in %s", exedir)
                    self.__uninstall_files__(exefiles, Path(exedir))
                else:
                    logging.error(
                        "Can't uninstall files %s: unknown location.", exefiles
                    )
            if remove:
                logging.info(f"Remove directory {gitdir}")
                shutil.rmtree(gitdir)
        else:
            logging.error(
                f"Can't install {plugin_id}: unknown installation method: {plugin['install']}"
            )
            sys.exit(5)
        del self.installed_plugins[plugin_id]

    def install_by_name(self, pluginname: str):
        """Install a plugin with the given name or id.

        If there are multiple plugins with the same name the user is asked to
        choose."""
        if pluginname in self.script_directory:
            return self.install(pluginname)
        else:
            plugins = []
            for key, value in self.script_directory.items():
                if value["name"] == pluginname:
                    plugins.append(key)
            return self.__install_from_list__(plugins)

    def search(self, seach_string: str):
        """Search names and descriptions of plugins."""
        plugins = []
        descriptions = []
        seach_string = seach_string.lower()
        for key, value in self.script_directory.items():
            if seach_string in value.get("name", ""):
                plugins.append(key)
                descriptions.append(value.get("desc", ""))
            elif seach_string in value.get("desc", "").lower():
                plugins.append(key)
                descriptions.append(value.get("desc", ""))
        self.__install_from_list__(plugins, descriptions)

    def __install_from_list__(
        self, plugins: List[str], descriptions: Optional[List[str]] = None
    ):
        """Ask the user which of the plugins should be installed."""
        logging.debug("Found %i potential plugins", len(plugins))
        if len(plugins) == 0:
            logging.error("No matching plugins found.")
            sys.exit(3)
        elif len(plugins) == 1:
            if ask_yes_no(f"Install {plugins[0]}?"):
                self.install(plugins[0])
            else:
                sys.exit(0)
        else:
            choise = ask_num("Found multiple plugins:", plugins, descriptions)
            if choise:
                self.install(choise)
            else:
                sys.exit(0)

    def install(self, plugin_id: str):
        """Install the plugin with the given plugin id."""
        plugin = self.script_directory[plugin_id].copy()
        term_width = shutil.get_terminal_size((80, 20)).columns
        wrapper = textwrap.TextWrapper(
            width=min(70, term_width), initial_indent="  ", subsequent_indent="  ",
        )

        if "install" not in plugin:
            errormsg = f"No installation method for {plugin_id}"
            explanation = """\
            This means, so far no one added the installation method to the mpv
            script directory. Doing so is most likely possible with just a few
            lines of JSON. Please add them and create a PR. You can find an
            introduction here:
            """
            url = "https://github.com/Nudin/mpv-script-directory/blob/master/HOWTO_ADD_INSTALL_INSTRUCTIONS.md"
            logging.error(errormsg)
            logging.error(wrapper.fill(textwrap.dedent(explanation)))
            logging.error(url)
            sys.exit(4)
        elif plugin["install"] == "git":
            gitdir = self.workdir / plugin["gitdir"]
            repourl = plugin["git"]
            scriptfiles = plugin.get("scriptfiles", [])
            shaderfiles = plugin.get("shaderfiles", [])
            fontfiles = plugin.get("fontfiles", [])
            scriptoptfiles = plugin.get("scriptoptfiles", [])
            exefiles = plugin.get("exefiles", [])
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
                exedir = ask_path("Where to put executable files?", Path("~/bin"))
                logging.info("Placing executables in %s", str(exedir))
                self.__install_files__(srcdir=gitdir, filelist=exefiles, dstdir=exedir)
                plugin["exedir"] = str(exedir)
        else:
            logging.error(
                f"Can't install {plugin_id}: unknown installation method: {plugin['install']}"
            )
            sys.exit(5)
        if "install-notes" in plugin:
            print(" " + plugin["install-notes"].replace("\n", "\n "))
        plugin["install_date"] = datetime.now().isoformat()
        self.installed_plugins[plugin_id] = plugin

    def upgrade(self):
        """Upgrade all repositories in the working directory."""
        for gitdir in self.workdir.glob("*/*"):
            logging.info("Updating repo in %s", gitdir)
            repo = Repo(gitdir)
            repo.remote().pull()

    def list_installed(self):
        """List all installed plugins"""
        logging.debug("%i installed plugins", len(self.installed_plugins))
        print("\n".join(self.installed_plugins.keys()))

    def __get_dirs__(self):
        """Find the directory paths by using environment variables or
        hardcoded fallbacks."""
        xdg_data = os.getenv("XDG_DATA_HOME")
        xdg_conf = os.getenv("XDG_CONFIG_HOME")
        appdata = os.getenv("APPDATA")
        mpv_home = os.getenv("MPV_HOME")
        # Directory for MPlug this is where all plugin files will be stored
        if xdg_data:
            self.workdir = Path(xdg_data) / "mplug"
        elif appdata:
            self.workdir = Path(appdata) / "mplug"
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
        self.directory_folder = self.workdir / self.directory_foldername

    @staticmethod
    def __clone_git__(repourl: str, gitdir: Path) -> Repo:
        """Clone or update a repository into a given folder."""
        if gitdir.exists():
            repo = Repo(gitdir)
            logging.debug("Repo already cloned, pull latest changes instead.")
            repo.remote().pull()
        else:
            repo = Repo.clone_from(repourl, gitdir, multi_options=["--depth 1"])
        return repo

    @staticmethod
    def __install_files__(srcdir: Path, filelist: List[str], dstdir: Path):
        """Install selected files as symlinks into the corresponding folder."""
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

    @staticmethod
    def __uninstall_files__(filelist: List[str], folder: Path):
        """Remove symlinks."""
        for file in filelist:
            filename = Path(file).name
            dst = folder / filename
            logging.info(f"Removing {dst}")
            if not dst.is_symlink():
                logging.critical(
                    "File %s is not a symlink! It apparently was not installed by %s. Aborting.",
                    dst,
                    NAME,
                )
                sys.exit(12)
            os.remove(dst)
