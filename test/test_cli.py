# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

import mplug
import pytest


def test_print_help():
    mplug.print_help()


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
            assert len(result) == 3
            assert result[1] is None
        for op in op_term:
            result = mplug.arg_parse([*argv, op, searchterm])
            assert isinstance(result, tuple)
            assert len(result) == 3
            assert result[1] == searchterm


def test_arg_parse_invalid_op():
    """Unknown operation: Print help and exit."""
    invalid_operations = ["invalid", "", None]
    for operation in invalid_operations:
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            mplug.arg_parse(["mplug", operation])
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code != 0


def test_arg_parse_missing_name():
    """Missing searchterm: Print help and exit."""
    operations = ["install", "uninstall", "search", "disable"]
    for operation in operations:
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            mplug.arg_parse(["mplug", operation])
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code != 0


def test_main(mocker):
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
