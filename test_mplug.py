#!/usr/bin/env python
# pylint: disable=redefined-outer-name,unused-argument
import collections
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import call

import pytest

import mplug


def test_print_help():
    mplug.print_help()


def test_ask_num_valid(mocker):
    """The user chooses one of the given options"""
    choices = ["foo", "bar", "baz"]
    for n, choice in enumerate(choices):
        mocker.patch("mplug.input", return_value=str(n))
        assert mplug.ask_num("Q?", choices) == choice


def test_ask_num_invalid(mocker):
    """The user enters an invalid input"""
    choices = ["foo", "bar", "baz"]
    invalid_strings = ["x", str(len(choices)), ""]
    for invalid in invalid_strings:
        mocker.patch("mplug.input", return_value=invalid)
        assert mplug.ask_num("Q?", choices) is None


def test_ask_yes_no_yes(mocker):
    """The user answers yes"""
    answers = ["y", "Y"]
    for input_str in answers:
        mocker.patch("mplug.input", return_value=input_str)
        assert mplug.ask_yes_no("Q?")


def test_ask_yes_no_no(mocker):
    """The user answers no or an invalid input"""
    answers = ["n", "N", "", "invalid_input"]
    for input_str in answers:
        mocker.patch("mplug.input", return_value=input_str)
        assert not mplug.ask_yes_no("Q?")


def test_ask_path(mocker):
    """The user enters a directory path"""
    mocker.patch("mplug.input", return_value="")
    default = Path("~/foo")
    assert mplug.ask_path("Q?", default) == default.expanduser()
    mocker.patch("mplug.input", return_value="~/bar")
    assert mplug.ask_path("Q?", default) == (Path.home() / "bar").expanduser()
    mocker.patch("mplug.input", return_value="/bar")
    assert mplug.ask_path("Q?", default) == (Path("/bar"))


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
        ],
    )
    current_timestamp = datetime.now().timestamp()
    return IO_Mocks(
        mocker.patch("mplug.open", mocker.mock_open()),
        mocker.patch("json.load", return_value={}),
        mocker.patch("json.dump", return_value=None),
        mocker.patch("os.makedirs", return_value=None),
        mocker.patch("os.symlink", return_value=None),
        mocker.patch("os.remove", return_value=None),
        mocker.patch("shutil.rmtree", return_value=None),
        mocker.patch("mplug.Repo.clone_from", return_value=None),
        mocker.patch("mplug.Repo.__init__", return_value=None),
        mocker.patch("mplug.Repo.remote", return_value=mocker.Mock()),
        mocker.patch("mplug.Path.exists", return_value=True),
        mocker.patch("mplug.Path.glob", return_value=[]),
        mocker.patch("mplug.Path.is_symlink", return_value=True),
        mocker.patch(
            "mplug.Path.stat", return_value=mocker.Mock(st_mtime=current_timestamp)
        ),
    )


@pytest.fixture(name="mpl")
def fixture_init_mplug(mock_files):
    """Return initialised MPlug.

    This fixture is basically the same as test_mplug_init_up2date."""
    mpl = mplug.MPlug()
    status_file = mpl.statefile
    assert mpl.script_directory == {}
    assert mpl.installed_scripts == {}
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
    assert mpl.installed_scripts == {}
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
    assert mpl.installed_scripts == {}
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
    assert mpl.installed_scripts == {}
    mock_files.json_load.assert_called()
    mock_files.open.assert_has_calls(
        [call(script_dir_file), call(status_file)], any_order=True
    )


def test_mplug_init_no_state_file(mock_files):
    """Test initialisation when the state-file is missing."""
    mock_files.json_load.side_effect = [None, FileNotFoundError]
    mpl = mplug.MPlug()
    assert mpl.installed_scripts == {}


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
    mock_yes_no = mocker.patch("mplug.ask_yes_no", return_value=False)
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
    mock_yes_no = mocker.patch("mplug.ask_yes_no", return_value=False)
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
    mock_input = mocker.patch("mplug.ask_yes_no", return_value=True)
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
    mock_ask_num = mocker.patch("mplug.ask_num", return_value=None)
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
    mock_input = mocker.patch("mplug.input", return_value="1")
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


def test_mplug_install_by_id_git(mpl, mock_files):
    """Successfully install a plugin by it's id via git."""
    mock_files.Path_exists.return_value = False
    script_id = "script_id"
    repo_url = " git_url"
    mpl.script_directory[script_id] = {
        "name": script_id,
        "install": "git",
        "git": repo_url,
        "gitdir": "gitdir",
        "scriptfiles": ["file1"],
        "install-notes": "Message to be shown after the install.",
    }
    gitdir = mpl.workdir / "gitdir"
    mpl.install_by_name(script_id)
    mock_files.Repo_clone_from.assert_called_with(repo_url, gitdir)
    mock_files.os_symlink.assert_called_once()
    assert mpl.installed_scripts != {}


@pytest.fixture()
def fixture_installed_plugin(mpl, mock_files):
    """Successfully install a plugin by it's id via git.

    This fixture is used to test uninstallments, it is basically identical to
    test_mplug_install_by_id_git."""
    mock_files.Path_exists.return_value = False
    script_id = "script_id"
    repo_url = " git_url"
    mpl.script_directory[script_id] = {
        "name": script_id,
        "install": "git",
        "git": repo_url,
        "gitdir": "gitdir",
        "scriptfiles": ["file1"],
        "install-notes": "Message to be shown after the install.",
    }
    gitdir = mpl.workdir / "gitdir"
    mpl.install_by_name(script_id)
    mock_files.Repo_clone_from.assert_called_with(repo_url, gitdir)
    mock_files.os_symlink.assert_called_once()
    assert mpl.installed_scripts != {}
    return mpl


def test_mplug_install_by_id_git_filepresent(mpl, mock_files, mocker):
    """Successfully install a plugin by it's id via git. The symlink already
    exists."""
    mock_files.Path_exists.return_value = True
    mock_repo_clone = mocker.spy(mplug.MPlug, "__clone_git__")
    searchterm = "searchterm"
    repo_url = " git_url"
    mpl.script_directory[searchterm] = {
        "name": searchterm,
        "install": "git",
        "git": repo_url,
        "gitdir": "gitdir",
        "scriptfiles": ["file1"],
    }
    mpl.install_by_name(searchterm)
    mock_repo_clone.assert_called()
    mock_files.os_symlink.assert_not_called()
    assert len(mpl.installed_scripts) == 1


def test_mplug_install_by_id_git_repopresent(mpl, mock_files):
    """Successfully install a plugin by it's id via git. The repo is already
    present."""
    mock_files.Path_exists.return_value = True
    searchterm = "searchterm"
    repo_url = " git_url"
    mpl.script_directory[searchterm] = {
        "name": searchterm,
        "install": "git",
        "git": repo_url,
        "gitdir": "gitdir",
        "scriptfiles": ["file1"],
    }
    mpl.install_by_name(searchterm)
    mock_files.Repo_init.assert_called()
    mock_files.Repo_remote.assert_called_with()
    mock_files.Repo_remote().pull.assert_called_with()
    mock_files.os_symlink.assert_not_called()
    assert len(mpl.installed_scripts) == 1


def test_mplug_install_by_id_git_withexe(mpl, mocker, mock_files):
    """Successfully install and uninstall a plugin containing an executable."""
    mock_files.Path_exists.return_value = False
    exedir = "path_of_executables"
    mocker.patch("mplug.ask_path", return_value=Path(exedir))
    script_id = "script_id"
    repo_url = " git_url"
    filename = "executable_file"
    mpl.script_directory[script_id] = {
        "name": script_id,
        "install": "git",
        "git": repo_url,
        "gitdir": "gitdir",
        "exefiles": [filename],
    }
    script_dir = mpl.workdir / "gitdir"
    src_file = script_dir / filename
    dst_file = Path(exedir) / filename
    mpl.install_by_name(script_id)
    mock_files.Repo_clone_from.assert_called_with(repo_url, script_dir)
    mock_files.os_symlink.assert_called_once_with(src_file, dst_file)
    assert mpl.installed_scripts != {}
    assert mpl.installed_scripts[script_id]["exedir"] == exedir
    mpl.uninstall(script_id)
    mock_files.shutil_rmtree.assert_called_once_with(script_dir)
    mock_files.os_remove.assert_called_once_with(dst_file)
    assert mpl.installed_scripts == {}


def test_mplug_upgrade(mpl, mock_files):
    """Upgrade multiple plugins."""
    script_list = ["foo", "bar"]
    call_list = [call(s) for s in script_list]
    mock_files.Path_glob.return_value = script_list
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
    script_id = "script_id"
    script = mpl.installed_scripts[script_id]
    file_calls = [call(mpl.scriptdir / file) for file in script["scriptfiles"]]
    script_dir = mpl.workdir / script["gitdir"]
    mpl.uninstall(script_id)
    mock_files.shutil_rmtree.assert_called_with(script_dir)
    mock_files.os_remove.assert_has_calls(file_calls)
    assert mpl.installed_scripts == {}


def test_mplug_uninstall_by_id_no_method(mpl):
    """Try to install a plugin, that has no installation method."""
    searchterm = "searchterm"
    mpl.script_directory[searchterm] = {"name": searchterm}
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.uninstall(searchterm)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0


def test_mplug_uninstall_by_id_unknown_method(mpl):
    """Try to install a plugin, that has an invalid/unknown installation method."""
    searchterm = "searchterm"
    mpl.script_directory[searchterm] = {"name": searchterm, "install": "unknown_method"}
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.uninstall(searchterm)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0


def test_mplug_uninstall_missing(fixture_installed_plugin):
    """Try to uninstall a plugin that is not installed."""
    mpl = fixture_installed_plugin
    prev_installed_scripts = mpl.installed_scripts.copy()
    script_id = "not_existent_script_id"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.uninstall(script_id)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0
    assert mpl.installed_scripts == prev_installed_scripts


def test_mplug_uninstall_wrong_file(fixture_installed_plugin, mock_files):
    """Try to uninstall a plugin that has a file that is not a symlink, meaning
    not (correctly) created by MPlug."""
    mpl = fixture_installed_plugin
    prev_installed_scripts = mpl.installed_scripts.copy()
    mock_files.Path_is_symlink.return_value = False
    script_id = "script_id"
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mpl.uninstall(script_id)
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code != 0
    assert mpl.installed_scripts == prev_installed_scripts


def test_arg_parse_help():
    """Print help and exit."""
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mplug.arg_parse(["mplug", "help"])
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        mplug.arg_parse(["mplug"])
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_arg_parse_valid():
    """Parse all valid input combinations."""
    op_term = ["install", "uninstall", "search", "disable"]
    op_no_term = ["upgrade", "update", "list-installed"]
    verbosity = [None, "-v"]
    searchterm = "searchterm"
    for flag in verbosity:
        argv = ["mplug"]
        if flag:
            argv.append(flag)
        for op in op_no_term:
            result = mplug.arg_parse([*argv, op])
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert result[1] is None
        for op in op_term:
            result = mplug.arg_parse([*argv, op, searchterm])
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert result[1] == searchterm


def test_arg_parse_invalid_op(mock_files):
    """Unknown operation: Print help and exit."""
    invalid_operations = ["invalid", "", None]
    for operation in invalid_operations:
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            mplug.arg_parse(["mplug", operation])
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code != 0


def test_arg_parse_missing_name(mock_files):
    """Missing searchterm: Print help and exit."""
    operations = ["install", "uninstall", "search", "disable"]
    for operation in operations:
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            mplug.arg_parse(["mplug", operation])
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code != 0


def test_main(mock_files, mocker):
    """Call all operations and make sure that only the right function is
    called."""
    mock_save_state = mocker.patch("mplug.MPlug.save_state_to_disk")
    mock_install_by_name = mocker.patch("mplug.MPlug.install_by_name")
    mock_search = mocker.patch("mplug.MPlug.search")
    mock_uninstall = mocker.patch("mplug.MPlug.uninstall")
    mock_list_installed = mocker.patch("mplug.MPlug.list_installed")
    mock_update = mocker.patch("mplug.MPlug.update")
    mock_upgrade = mocker.patch("mplug.MPlug.upgrade")
    argmap = {
        "install": mock_install_by_name,
        "search": mock_search,
        "uninstall": mock_uninstall,
        "disable": mock_uninstall,
        "update": mock_update,
        "upgrade": mock_upgrade,
        "list-installed": mock_list_installed,
    }
    ops_mock_list = set(argmap.values())
    for arg, mock in argmap.items():
        mplug.main(arg, "searchterm")

        for mock_op in ops_mock_list:
            if mock_op is not mock:
                mock_op.assert_not_called()
            else:
                mock.assert_called_once()
            mock_op.reset_mock()
        mock_save_state.assert_called_once_with()
        mock_save_state.reset_mock()
