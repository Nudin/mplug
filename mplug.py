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

from git import Repo


def ask_num(question, options):
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
        return False
    except AssertionError:
        return False


def ask_yes_no(question):
    answer = input(f"{question} [y/N] ")
    if answer in ["y", "Y"]:
        return True
    return False


class MPlug:
    MPV_SCRIPT_DIR_DIR = "mpv_script_dir"
    MPV_SCRIPT_DIR = "mpv_script_directory.json"
    MPV_SCRIPT_DIR_REPO = "https://github.com/Nudin/mpv-script-directory.git"

    def __init__(self):
        self.get_dirs()
        script_dir_file = self.script_dir_repo / self.MPV_SCRIPT_DIR
        if not self.script_dir_repo.exists():
            self.update()
        else:
            age = datetime.now().timestamp() - script_dir_file.stat().st_mtime
            if age > 60 * 60 * 24 * 30:
                self.update()
        with open(script_dir_file) as f:
            self.script_dir = json.load(f)

    def update(self):
        print(f"Updating {self.MPV_SCRIPT_DIR}")
        self.clone_git(self.MPV_SCRIPT_DIR_REPO, self.script_dir_repo)

    def uninstall(self, name, remove=True):
        if name not in self.script_dir:
            print("Not installed")
            exit(10)
            return False
        script = self.script_dir[name]
        if "install" not in script:
            print(f"No installation method for {name}")
            exit(4)
        elif script["install"] == "git":
            gitdir = self.workdir / script["gitdir"]
            print(f"Remove directory {gitdir}")
            if remove:
                shutil.rmtree(gitdir)
            scriptfiles = script.get("scriptfiles", [])
            self.uninstall_files(scriptfiles)
        else:
            print(
                f"Can't install {name}: unknown installation method: {script['install']}"
            )
            exit(5)

    def find_install(self, name):
        if name in self.script_dir:
            return self.install(name)
        else:
            scripts = self.find(name)
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

    def install(self, name):
        script = self.script_dir[name]

        if "install" not in script:
            print(f"No installation method for {name}")
            exit(4)
        elif script["install"] == "git":
            gitdir = self.workdir / script["gitdir"]
            repourl = script["git"]
            scriptfiles = script.get("scriptfiles", [])
            self.clone_git(repourl, gitdir)
            self.install_files(gitdir, scriptfiles)
        else:
            print(
                f"Can't install {name}: unknown installation method: {script['install']}"
            )
            exit(5)

    def find(self, name):
        results = []
        for key, value in self.script_dir.items():
            if value["name"] == name:
                results.append(key)
        return results

    # Find out and create directories
    def get_dirs(self):
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
        self.script_dir_repo = self.workdir / self.MPV_SCRIPT_DIR_DIR

    # Clone repo
    def clone_git(self, repourl, gitdir):
        if gitdir.exists():
            repo = Repo(gitdir)
            repo.remote().pull()
        else:
            repo = Repo.clone_from(repourl, gitdir)
        return repo

    def upgrade(self):
        for gitdir in self.workdir.glob("*/*"):
            repo = Repo(gitdir)
            repo.remote().pull()

    # Install all script files as symlinks
    def install_files(self, srcdir, scriptfiles):
        if not self.scriptdir.exists():
            os.mkdir(self.scriptdir)
        for file in scriptfiles:
            src = srcdir / file
            dst = self.scriptdir / file
            if dst.exists():
                print("File already exists:", dst)
                continue
            os.symlink(src, dst)

    def uninstall_files(self, scriptfiles):
        for file in scriptfiles:
            dst = self.scriptdir / file
            print(f"Removing {dst}")
            os.remove(dst)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        exit(0)
    operation = sys.argv[1]

    if operation not in ["install", "upgrade", "uninstall", "update", "disable"]:
        exit(1)

    if operation in ["install", "uninstall"] and len(sys.argv) < 3:
        exit(2)

    # Load script directory
    plug = MPlug()

    if operation == "install":
        name = sys.argv[2]
        plug.find_install(name)
    elif operation == "uninstall":
        name = sys.argv[2]
        plug.uninstall(name)
    elif operation == "update":
        plug.update()
    elif operation == "upgrade":
        plug.upgrade()
    elif operation == "disable":
        plug.uninstall(name, remove=False)
