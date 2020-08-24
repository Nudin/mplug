# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) Michael F. Schönitzer, 2020

from pathlib import Path

from mplug.interaction import ask_num, ask_path, ask_yes_no


def test_ask_num_valid(mocker):
    """The user chooses one of the given options"""
    choices = ["foo", "bar", "baz"]
    for n, choice in enumerate(choices):
        mocker.patch("mplug.interaction.input", return_value=str(n))
        assert ask_num("Q?", choices) == choice


def test_ask_num_invalid(mocker):
    """The user enters an invalid input"""
    choices = ["foo", "bar", "baz"]
    invalid_strings = ["x", str(len(choices)), ""]
    for invalid in invalid_strings:
        mocker.patch("mplug.interaction.input", return_value=invalid)
        assert ask_num("Q?", choices) is None


def test_ask_yes_no_yes(mocker):
    """The user answers yes"""
    answers = ["y", "Y"]
    for input_str in answers:
        mocker.patch("mplug.interaction.input", return_value=input_str)
        assert ask_yes_no("Q?")


def test_ask_yes_no_no(mocker):
    """The user answers no or an invalid input"""
    answers = ["n", "N", "", "invalid_input"]
    for input_str in answers:
        mocker.patch("mplug.interaction.input", return_value=input_str)
        assert not ask_yes_no("Q?")


def test_ask_path(mocker):
    """The user enters a directory path"""
    mocker.patch("mplug.interaction.input", return_value="")
    default = Path("~/foo")
    assert ask_path("Q?", default) == default.expanduser()
    mocker.patch("mplug.interaction.input", return_value="~/bar")
    assert ask_path("Q?", default) == (Path.home() / "bar").expanduser()
    mocker.patch("mplug.interaction.input", return_value="/bar")
    assert ask_path("Q?", default) == (Path("/bar"))
