# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020
"""
Main module containing the main class MPlug.

The MPlug class is the plugin manager that has functions that can be called to
install, uninstall or query plugins.
MPlug works using the `mpv script directory`, see here for details:
https://github.com/Nudin/mpv-script-directory
"""

import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .download import download_file, download_tar, git_clone_or_pull, git_pull
from .interaction import ask_num, ask_path, ask_yes_no, check_os
from .util import make_files_executable, resolve_templates, wrap

NAME = "mplug"


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

    def __init__(self, verbose=False):
        """Initialise Plugin Manager.

        Clone the script directory if not already available, update it if it
        hasn't been updated since more then 30 days. Then read the directory.
        """
        self.verbose = verbose
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
        with open(script_dir_file) as file:
            self.script_directory = json.load(file)
        self.statefile = self.workdir / "installed_plugins"
        try:
            with open(self.statefile) as statefile:
                self.installed_plugins = json.load(statefile)
        except json.JSONDecodeError:
            logging.error(
                "Failed to load mplug file %s:", self.statefile, exc_info=True
            )
            sys.exit(11)
        except FileNotFoundError:
            logging.debug("No packages installed yet.")
            self.installed_plugins = {}

    def save_state_to_disk(self):
        """Write installed plugins on exit."""
        with open(self.statefile, "w") as statefile:
            json.dump(self.installed_plugins, statefile)
            logging.debug("Saving list of installed plugins")

    def update(self):
        """Get or update the 'mpv script directory'."""
        logging.info("Updating %s", self.directory_filename)
        git_clone_or_pull(self.directory_remoteurl, self.directory_folder)

    def uninstall(self, plugin_id: str, remove: bool = True):
        """Remove or disable a plugin.

        remove: if True the tools folder will be deleted from disc. If False
        only remove the symlinks to the files.
        """
        plugin = self.installed_plugins[plugin_id]
        logging.debug("Remove links of {plugin_id}")
        install_dir = self.workdir / plugin["install_dir"]
        for filetype, directory in self.installation_dirs.items():
            filelist = plugin.get(filetype, [])
            self.__uninstall_files__(filelist, directory)
        exefiles = plugin.get("exefiles", [])
        if exefiles:
            exedir = plugin.get("exedir")
            if exedir:
                logging.debug("Remove link to executables in %s", exedir)
                self.__uninstall_files__(exefiles, Path(exedir))
            else:
                logging.error("Can't uninstall files %s: unknown location.", exefiles)
        if remove:
            logging.info(f"Remove directory {install_dir}")
            shutil.rmtree(install_dir)
        if remove:
            del self.installed_plugins[plugin_id]
        else:
            plugin["state"] = "disabled"

    def uninstall_by_name(self, pluginname: str, remove: bool = True):
        """Uninstall a plugin with the given name or id."""
        if pluginname in self.script_directory:
            return self.uninstall(pluginname)
        else:
            potential_plugins = self.__plugin_id_by_name__(pluginname)
            if len(potential_plugins) == 0:
                logging.error("Not installed: %s", pluginname)
                sys.exit(10)
            elif len(potential_plugins) > 1:
                logging.error(
                    "Multiple matching plugins found, please specify plugin id."
                )
                sys.exit(10)
            elif ask_yes_no(f"Uninstall plugin {potential_plugins[0]}"):
                return self.uninstall(potential_plugins[0], remove)
            else:
                sys.exit(0)

    def install_by_name(self, pluginname: str):
        """Install a plugin with the given name or id.

        If there are multiple plugins with the same name the user is asked to
        choose."""
        if pluginname in self.script_directory:
            return self.install(pluginname)
        else:
            plugins = self.__plugin_id_by_name__(pluginname)
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

        if "install" not in plugin:
            errormsg = f"No installation method for {plugin_id}"
            explanation = """\
            This means, so far no one added the installation method to the mpv
            script directory. Doing so is most likely possible with just a few
            lines of JSON. Please add them and create a PR. You can find an
            introduction here:
            """
            url = "https://github.com/Nudin/mpv-script-directory/"
            url += "blob/master/HOWTO_ADD_INSTALL_INSTRUCTIONS.md"
            logging.error(errormsg)
            logging.error(wrap(explanation, indent=1, dedent=True))
            logging.error(url)
            sys.exit(4)

        if not check_os(plugin.get("os", [])):
            sys.exit(0)
        try:
            install_dir = self.workdir / plugin["install_dir"]
            url = resolve_templates(plugin["receiving_url"])
        except KeyError as keyerror:
            logging.error("Missing field %s", keyerror.args[0])
            sys.exit(13)
        if plugin["install"] == "git":
            logging.debug("Clone git repo %s to %s", url, install_dir)
            git_clone_or_pull(url, install_dir)
        elif plugin["install"] == "url":
            filename = plugin["filename"]
            logging.debug("Downloading %s to %s", url, install_dir)
            download_file(url, install_dir / filename)
        elif plugin["install"] == "tar":
            logging.debug("Downloading %s to %s", url, install_dir)
            download_tar(url, install_dir)
        else:
            logging.error(
                f"Can't install {plugin_id}: unknown installation method: {plugin['install']}"
            )
            sys.exit(5)
        for filetype, directory in self.installation_dirs.items():
            filelist = plugin.get(filetype, [])
            self.__install_files__(
                srcdir=install_dir, filelist=filelist, dstdir=directory
            )
        if "ladspafiles" in plugin and os.getenv("LADSPA_PATH") is None:
            logging.warning(
                "Set the environment variable LADSPA_PATH to '%s'.",
                self.installation_dirs["ladspafiles"],
            )
        if "exefiles" in plugin:
            exedir = ask_path("Where to put executable files?", Path("~/bin"))
            logging.info("Placing executables in %s", str(exedir))
            installed = self.__install_files__(
                srcdir=install_dir, filelist=plugin["exefiles"], dstdir=exedir
            )
            make_files_executable(installed)
            plugin["exedir"] = str(exedir)
        if "install-notes" in plugin:
            print(wrap(plugin["install-notes"]))
        plugin["install_date"] = datetime.now().isoformat()
        plugin["state"] = "active"
        self.installed_plugins[plugin_id] = plugin

    def upgrade(self):
        """Upgrade all repositories in the working directory."""
        self.update()
        for plugin in self.installed_plugins.values():
            logging.info("Updating plugin %s", plugin["name"])
            install_dir = self.workdir / plugin["install_dir"]
            url = resolve_templates(plugin["receiving_url"])
            if plugin["install"] == "git":
                logging.debug("Updating repo in %s", install_dir)
                git_pull(install_dir)
            elif plugin["install"] == "tar":
                logging.debug("Downloading %s to %s", url, install_dir)
                download_tar(url, install_dir)
            elif plugin["install"] == "url":
                filename = resolve_templates(plugin["filename"])
                logging.debug("Downloading %s to %s", url, install_dir)
                download_file(url, install_dir / filename)
            else:
                logging.error("Cannot upgrade %s – installation directory.")

    def list_installed(self):
        """List all installed plugins"""
        logging.debug("%i installed plugins", len(self.installed_plugins))
        for plugin_id, plugin in self.installed_plugins.items():
            text = plugin_id
            if plugin.get("state") == "disabled":
                text += " [DISABLED]"
            print(wrap(text, indent=int(self.verbose)))
            if self.verbose:
                print(wrap(plugin["desc"], indent=2))

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
        # directory for ladspa filters, fallback according to:
        # https://www.ladspa.org/ladspa_sdk/shared_plugins.html
        ladspa_path = os.getenv("LADSPA_PATH")
        if ladspa_path:
            ladspa_dir = Path(ladspa_path.split(":")[0])
        else:
            ladspa_dir = Path.home() / ".ladspa"
        self.installation_dirs = {
            "scriptfiles": self.mpvdir / "scripts",
            "shaderfiles": self.mpvdir / "shaders",
            "fontfiles": self.mpvdir / "fonts",
            "scriptoptfiles": self.mpvdir / "script-opts",
            "ladspafiles": ladspa_dir,
        }
        # Directory for MPlug this is where all plugin files will be stored
        self.directory_folder = self.workdir / self.directory_foldername

    def __plugin_id_by_name__(self, pluginname: str) -> List[str]:
        """Get the ids of all plugins with the give name."""
        plugins = []
        for key, value in self.script_directory.items():
            if value["name"] == pluginname:
                plugins.append(key)
        return plugins

    @staticmethod
    def __install_files__(
        srcdir: Path, filelist: List[str], dstdir: Path
    ) -> List[Path]:
        """Install selected files as symlinks into the corresponding folder."""
        if not dstdir.exists():
            logging.debug("Create directory %s", dstdir)
            os.makedirs(dstdir)
        installed_files = []
        for file in filelist:
            file = resolve_templates(file)
            src = srcdir / file
            filename = Path(file).name
            if not src.exists():
                # pylint: disable=W1201
                logging.error(
                    "File %s does not exsist. "
                    + "Check information in mpv script directory for correctness.",
                    src,
                )
                sys.exit(14)
            dst = dstdir / filename
            if dst.exists() and not dst.is_symlink():
                logging.error(
                    "File already exists and is not a symlink: %s Aborting.", dst
                )
                sys.exit(15)
            if dst.is_symlink() and dst.resolve() != src.resolve():
                logging.info(
                    "File already exists and points to wrong target: %s -> %s",
                    dst,
                    dst.resolve(),
                )
                if ask_yes_no("Overwrite file?"):
                    os.remove(dst)
                else:
                    sys.exit(15)
            if dst.is_symlink() and dst.resolve() == src.resolve():
                logging.info("File already exists: %s", dst)
                continue
            logging.debug("Copying file %s to %s", filename, dst)
            os.symlink(src, dst)
            installed_files.append(dst)
        return installed_files

    @staticmethod
    def __uninstall_files__(filelist: List[str], folder: Path):
        """Remove symlinks."""
        for file in filelist:
            file = resolve_templates(file)
            filename = Path(file).name
            dst = folder / filename
            logging.info(f"Removing {dst}")
            if not dst.exists():
                continue
            if not dst.is_symlink():
                logging.critical(
                    "File %s is not a symlink! It apparently was not installed by %s. Aborting.",
                    dst,
                    NAME,
                )
                sys.exit(12)
            os.remove(dst)
