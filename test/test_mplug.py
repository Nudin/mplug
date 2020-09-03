#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

# pylint: disable=redefined-outer-name,unused-argument
import collections
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import call

import mplug
import pytest


@pytest.fixture(name="mock_files")
def fixture_mock_files(mocker):
    """Mock all used functions that do disc IO.

    These unit tests should never actually read from or write to disc, or
    depend on the state of files in the file system. This fixture replaces all
    calls to such functions by mocks. The mocks are returned as namedtuple, so
    that their return value can be adjusted in tests and their calls can be
    asserted.
    """
    IO_Mocks = collections.namedtuple(
        "IO_Mocks",
        [
            "open",
            "json_load",
            "json_dump",
            "os_makedirs",
            "os_symlink",
            "os_remove",
            "shutil_rmtree",
            "Repo_clone_from",
            "Repo_init",
            "Repo_remote",
            "Path_exists",
            "Path_glob",
            "Path_is_symlink",
            "Path_stat",
            "Path_resolve",
        ],
    )
    current_timestamp = datetime.now().timestamp()
    return IO_Mocks(
        mocker.patch("mplug.mplug.open", mocker.mock_open()),
        mocker.patch("json.load", return_value={}),
        mocker.patch("json.dump", return_value=None),
        mocker.patch("os.makedirs", return_value=None),
        mocker.patch("os.symlink", return_value=None),
        mocker.patch("os.remove", return_value=None),
        mocker.patch("shutil.rmtree", return_value=None),
        mocker.patch("mplug.mplug.Repo.clone_from", return_value=None),
        mocker.patch("mplug.mplug.Repo.__init__", return_value=None),
        mocker.patch("mplug.mplug.Repo.remote", return_value=mocker.Mock()),
        mocker.patch("mplug.mplug.Path.exists", return_value=True),
        mocker.patch("mplug.mplug.Path.glob", return_value=[]),
        mocker.patch("mplug.mplug.Path.is_symlink", return_value=True),
        mocker.patch(
            "mplug.mplug.Path.stat",
            return_value=mocker.Mock(st_mtime=current_timestamp),
        ),
        mocker.patch("mplug.mplug.Path.resolve", return_value=Path(".")),
    )


@pytest.fixture(name="mpl")
def fixture_init_mplug(mock_files):
    """Return initialised MPlug.

    This fixture is basically the same as test_mplug_init_up2date."""
    mpl = mplug.MPlug()
    status_file = mpl.statefile
    assert mpl.script_directory == {}
    assert mpl.installed_plugins == {}
    yield mpl
    mock_files.open.reset_mock()
    mpl.save_state_to_disk()
    mock_files.json_dump.assert_called_once()
    mock_files.open.assert_called_once_with(status_file, "w")


def test_mplug_init_up2date(mock_files):
    """Initialise MPlug.

    Case: script directory exists and is up to date
    """
    mpl = mplug.MPlug()
    script_dir_file = mpl.directory_folder / mpl.directory_filename
    status_file = mpl.statefile
    assert mpl.script_directory == {}
    assert mpl.installed_plugins == {}
    mock_files.json_load.assert_called()
    mock_files.open.assert_has_calls(
        [call(script_dir_file), call(status_file)], any_order=True
    )


def test_mplug_init_outdated(mock_files):
    """Initialise MPlug.

    Case: script directory exists but is outdated
    """
    mock_files.Path_stat().st_mtime = 0
    mpl = mplug.MPlug()
    script_dir_file = mpl.directory_folder / mpl.directory_filename
    status_file = mpl.statefile
    assert mpl.script_directory == {}
    assert mpl.installed_plugins == {}
    mock_files.json_load.assert_called()
    mock_files.open.assert_has_calls(
        [call(script_dir_file), call(status_file)], any_order=True
    )


def test_mplug_init_new(mock_files):
    """Initialise MPlug.

    Case: script directory does not yet exists
    """
    mock_files.Path_exists.return_value = False
    mpl = mplug.MPlug()
    script_dir_file = mpl.directory_folder / mpl.directory_filename
    status_file = mpl.statefile
    assert mpl.script_directory == {}
    assert mpl.installed_plugins == {}
    mock_files.json_load.assert_called()
    mock_files.open.assert_has_calls(
        [call(script_dir_file), call(status_file)], any_order=True
    )


def test_mplug_init_no_state_file(mock_files):
    """Test initialisation when the state-file is missing."""
    mock_files.json_load.side_effect = [None, FileNotFoundError]
    mpl = mplug.MPlug()
    assert mpl.installed_plugins == {}


def test_mplug_init_invalid_state(mock_files):
    """Test initialisation when the state-file is corrupt."""
    mock_files.json_load.side_effect = [None, json.JSONDecodeError("", "", 0)]
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mplug.MPlug()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0


def test_mplug_init_getmpvdir(mock_files, monkeypatch):
    """Check that the mplug working directory is set correctly
    based on the existence of different environment variables."""
    mpv_home_dir = "some_mpv_home_dir"
    wrong_dir = "wrong directory"
    # MPV_HOME set, others unset -> use MPV_HOME
    monkeypatch.setenv("MPV_HOME", mpv_home_dir)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    mpl = mplug.MPlug()
    assert mpl.mpvdir == Path(mpv_home_dir)

    # MPV_HOME set, others also set -> use MPV_HOME
    monkeypatch.setenv("MPV_HOME", mpv_home_dir)
    monkeypatch.setenv("XDG_CONFIG_HOME", wrong_dir)
    monkeypatch.setenv("APPDATA", wrong_dir)
    monkeypatch.setenv("XDG_DATA_HOME", wrong_dir)
    mpl = mplug.MPlug()
    assert mpl.mpvdir == Path(mpv_home_dir)

    # MPV_HOME unset, XDG_CONFIG_HOME set -> use XDG_CONFIG_HOME
    monkeypatch.delenv("MPV_HOME", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", mpv_home_dir)
    monkeypatch.setenv("APPDATA", wrong_dir)
    mpl = mplug.MPlug()
    assert mpl.mpvdir == Path(mpv_home_dir) / "mpv"

    # MPV_HOME unset, APPDATA set -> use APPDATA
    monkeypatch.delenv("MPV_HOME", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("APPDATA", mpv_home_dir)
    mpl = mplug.MPlug()
    assert mpl.mpvdir == Path(mpv_home_dir) / "mpv"

    # nothing set -> fallback ~/.mpv
    monkeypatch.delenv("MPV_HOME", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    mpl = mplug.MPlug()
    assert mpl.mpvdir == Path.home() / ".mpv"


def test_mplug_init_getworkdir(mock_files, monkeypatch):
    """Check that the mpv configuration directory is detected correctly
    based on the existence of different environment variables."""
    datadir = "some datadir"
    wrong_dir = "wrong directory"
    # MPV_HOME and XDG_CONFIG_HOME should not matter for this
    monkeypatch.setenv("MPV_HOME", wrong_dir)
    monkeypatch.setenv("XDG_CONFIG_HOME", wrong_dir)
    # Use XDG_DATA_HOME if present
    monkeypatch.setenv("XDG_DATA_HOME", datadir)
    monkeypatch.delenv("APPDATA", raising=False)
    mpl = mplug.MPlug()
    assert mpl.workdir == Path(datadir) / "mplug"

    # Use APPDATA if present
    monkeypatch.setenv("APPDATA", datadir)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    mpl = mplug.MPlug()
    assert mpl.workdir == Path(datadir) / "mplug"

    # Fallback to ~/.mplug
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    mpl = mplug.MPlug()
    assert mpl.workdir == Path.home() / ".mplug"


def test_mplug_install_by_name_nomatch(mpl):
    """Try to install an unknown plugin."""
    searchterm_without_matches = "searchterm_without_matches"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.install_by_name(searchterm_without_matches)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0


def test_mplug_install_by_name_onematch_decline(mpl, mocker):
    """Try to install a plugin, but then cancel the installation."""
    searchterm = "searchterm"
    mpl.script_directory["uniq-id"] = {"name": searchterm}
    mock_yes_no = mocker.patch("mplug.mplug.ask_yes_no", return_value=False)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.install_by_name(searchterm)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    mock_yes_no.assert_called_once()


def test_mplug_search_onematch_decline(mpl, mocker):
    """Search for a plugin, but then cancel the installation."""
    searchterm = "searchterm"
    mpl.script_directory["uniq-id"] = {
        "name": "name",
        "desc": f"something {searchterm} something",
    }
    mock_yes_no = mocker.patch("mplug.mplug.ask_yes_no", return_value=False)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.search(searchterm)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    mock_yes_no.assert_called_once()


def test_mplug_search_onematche_choose(mpl, mocker):
    """Search for a plugin, and choose the only match."""
    searchterm = "searchterm"
    mpl.script_directory["uniq-id"] = {
        "name": "name",
        "desc": f"something {searchterm} something",
    }
    mock_input = mocker.patch("mplug.mplug.ask_yes_no", return_value=True)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.search(searchterm)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0
    mock_input.assert_called_once()


def test_mplug_search_multiplematches_decline(mpl, mocker):
    """Search for a plugin (multiple results), but then cancel the
    installation."""
    searchterm = "searchterm"
    mpl.script_directory["uniq-id"] = {
        "name": "name",
        "desc": f"something {searchterm} something",
    }
    mpl.script_directory["uniq-id2"] = {
        "name": f"something {searchterm} something",
        "desc": "description",
    }
    mock_ask_num = mocker.patch("mplug.mplug.ask_num", return_value=None)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.search(searchterm)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    mock_ask_num.assert_called_once()


def test_mplug_search_multiplematches_choose(mpl, mocker):
    """Search for a plugin (multiple results), and choose the first match."""
    searchterm = "searchterm"
    mpl.script_directory["uniq-id"] = {
        "name": "name",
        "desc": f"something {searchterm} something",
    }
    mpl.script_directory["uniq-id2"] = {
        "name": f"something {searchterm} something",
        "desc": "description",
    }
    mock_input = mocker.patch("mplug.interaction.input", return_value="1")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.search(searchterm)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0
    mock_input.assert_called_once()


def test_mplug_install_by_id_no_method(mpl):
    """Try to install a plugin, that has no installation method."""
    searchterm = "searchterm"
    mpl.script_directory[searchterm] = {"name": searchterm}
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.install_by_name(searchterm)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0


def test_mplug_install_by_id_unknown_method(mpl):
    """Try to install a plugin, that has an invalid/unknown installation method."""
    searchterm = "searchterm"
    mpl.script_directory[searchterm] = {"name": searchterm, "install": "unknown_method"}
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.install_by_name(searchterm)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0


def test_mplug_install_by_id_git(mpl, mock_files, mocker):
    """Successfully install a plugin by it's id via git."""
    mock_files.Path_exists.return_value = False
    install = mocker.patch("mplug.mplug.MPlug.__install_files__", return_value=None)
    plugin_id = "plugin_id"
    repo_url = " git_url"
    mpl.script_directory[plugin_id] = {
        "name": plugin_id,
        "install": "git",
        "receiving_url": repo_url,
        "install_dir": "install_dir",
        "scriptfiles": ["file1"],
        "install-notes": "Message to be shown after the install.",
    }
    install_dir = mpl.workdir / "install_dir"
    mpl.install_by_name(plugin_id)
    mock_files.Repo_clone_from.assert_called_with(
        repo_url, install_dir, multi_options=["--depth 1"]
    )
    install.assert_called()
    assert mpl.installed_plugins != {}


@pytest.fixture()
def fixture_installed_plugin(mpl, mock_files, mocker):
    """Successfully install a plugin by it's id via git.

    This fixture is used to test uninstallments, it is basically identical to
    test_mplug_install_by_id_git."""
    mock_files.Path_is_symlink.return_value = False
    mock_files.Path_exists.return_value = False
    install = mocker.patch("mplug.mplug.MPlug.__install_files__", return_value=None)
    plugin_id = "plugin_id"
    repo_url = " git_url"
    mpl.script_directory[plugin_id] = {
        "name": plugin_id,
        "install": "git",
        "receiving_url": repo_url,
        "install_dir": "install_dir",
        "scriptfiles": ["file1"],
        "install-notes": "Message to be shown after the install.",
    }
    install_dir = mpl.workdir / "install_dir"
    mpl.install_by_name(plugin_id)
    mock_files.Repo_clone_from.assert_called_with(
        repo_url, install_dir, multi_options=["--depth 1"]
    )
    install.assert_called()
    assert mpl.installed_plugins != {}
    return mpl


def test_mplug_install_by_id_git_filepresent(mpl, mock_files, mocker):
    """Successfully install a plugin by it's id via git. The symlink already
    exists."""
    mock_files.Path_is_symlink.return_value = True
    mock_files.Path_exists.return_value = True
    mock_repo_clone = mocker.spy(mplug.MPlug, "__clone_git__")
    searchterm = "searchterm"
    repo_url = " git_url"
    mpl.script_directory[searchterm] = {
        "name": searchterm,
        "install": "git",
        "receiving_url": repo_url,
        "install_dir": "install_dir",
        "scriptfiles": ["file1"],
    }
    mpl.install_by_name(searchterm)
    mock_repo_clone.assert_called()
    mock_files.os_symlink.assert_not_called()
    assert len(mpl.installed_plugins) == 1


def test_mplug_install_by_id_git_repopresent(mpl, mock_files):
    """Successfully install a plugin by it's id via git. The repo is already
    present."""
    mock_files.Path_exists.return_value = True
    searchterm = "searchterm"
    repo_url = " git_url"
    mpl.script_directory[searchterm] = {
        "name": searchterm,
        "install": "git",
        "receiving_url": repo_url,
        "install_dir": "install_dir",
        "scriptfiles": ["file1"],
    }
    mpl.install_by_name(searchterm)
    mock_files.Repo_init.assert_called()
    mock_files.Repo_remote.assert_called_with()
    mock_files.Repo_remote().pull.assert_called_with()
    mock_files.os_symlink.assert_not_called()
    assert len(mpl.installed_plugins) == 1


def test_mplug_install_by_id_git_withexe(mpl, mocker, mock_files):
    """Successfully install and uninstall a plugin containing an executable."""
    mock_files.Path_exists.return_value = False
    install = mocker.patch("mplug.mplug.MPlug.__install_files__", return_value=None)
    exedir = "path_of_executables"
    mocker.patch("mplug.mplug.ask_path", return_value=Path(exedir))
    plugin_id = "plugin_id"
    repo_url = " git_url"
    filename = "executable_file"
    mpl.script_directory[plugin_id] = {
        "name": plugin_id,
        "install": "git",
        "receiving_url": repo_url,
        "install_dir": "install_dir",
        "exefiles": [filename],
    }
    plugin_dir = mpl.workdir / "install_dir"
    dst_file = Path(exedir) / filename
    mpl.install_by_name(plugin_id)
    mock_files.Repo_clone_from.assert_called_with(
        repo_url, plugin_dir, multi_options=["--depth 1"]
    )
    assert mpl.installed_plugins != {}
    assert plugin_id in mpl.installed_plugins
    assert mpl.installed_plugins[plugin_id]["exedir"] == exedir
    install.assert_called()
    mock_files.Path_exists.return_value = True
    mpl.uninstall(plugin_id)
    mock_files.shutil_rmtree.assert_called_once_with(plugin_dir)
    mock_files.os_remove.assert_called_once_with(dst_file)
    assert mpl.installed_plugins == {}


def test_mplug_upgrade(mpl, mock_files):
    """Upgrade multiple plugins."""
    mpl.installed_plugins = {
        "foo": {
            "install": "git",
            "receiving_url": "url",
            "name": "foo",
            "install_dir": "foodir",
        },
        "bar": {
            "install": "git",
            "receiving_url": "url",
            "name": "bar",
            "install_dir": "bardir",
        },
    }
    call_list = [
        call(mpl.workdir / plugin["install_dir"])
        for plugin in mpl.installed_plugins.values()
    ]
    mpl.upgrade()
    mock_files.Repo_init.assert_has_calls(call_list)
    mock_files.Repo_remote.assert_called_with()
    mock_files.Repo_remote().pull.assert_called_with()


def test_mplug_list_installed(mpl):
    """List all installed plugins."""
    mpl.list_installed()


def test_mplug_uninstall(fixture_installed_plugin, mock_files):
    """Uninstall a previously installed plugin."""
    mpl = fixture_installed_plugin
    mock_files.Path_is_symlink.return_value = True
    plugin_id = "plugin_id"
    plugin = mpl.installed_plugins[plugin_id]
    scriptdir = mpl.installation_dirs["scriptfiles"]
    file_calls = [call(scriptdir / file) for file in plugin["scriptfiles"]]
    plugin_dir = mpl.workdir / plugin["install_dir"]
    mock_files.Path_exists.return_value = True
    mpl.uninstall(plugin_id)
    mock_files.shutil_rmtree.assert_called_with(plugin_dir)
    mock_files.os_remove.assert_has_calls(file_calls)
    assert mpl.installed_plugins == {}


def test_mplug_uninstall_missing(fixture_installed_plugin):
    """Try to uninstall a plugin that is not installed."""
    mpl = fixture_installed_plugin
    prev_installed_plugins = mpl.installed_plugins.copy()
    plugin_id = "not_existent_plugin_id"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.uninstall_by_name(plugin_id)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0
    assert mpl.installed_plugins == prev_installed_plugins


def test_mplug_uninstall_wrong_file(fixture_installed_plugin, mock_files):
    """Try to uninstall a plugin that has a file that is not a symlink, meaning
    not (correctly) created by MPlug."""
    mpl = fixture_installed_plugin
    prev_installed_plugins = mpl.installed_plugins.copy()
    mock_files.Path_is_symlink.return_value = False
    plugin_id = "plugin_id"
    mock_files.Path_exists.return_value = True
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.uninstall(plugin_id)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0
    assert mpl.installed_plugins == prev_installed_plugins
