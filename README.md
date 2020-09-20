MPlug – a Plugin Manager for MPV
================================

A plugin manager for [mpv](https://mpv.io/) to easy install and uninstall mpv scripts and more.

Motivation
----------
Mpv is a great, free and open source video player. It has interfaces to extend
it with different types of scripts and filters. There is a large number of
awesome plugins: Watch [Youtube](https://youtube-dl.org/), [remove black bars](https://github.com/mpv-player/mpv/blob/master/TOOLS/lua/autocrop.lua), [improve the quality of Anime](https://github.com/bloc97/Anime4K),
[remove noise from lecture recordings](https://github.com/werman/noise-suppression-for-voice), [skip adds](https://github.com/po5/mpv_sponsorblock)… The possibilities are endless.

MPlug tries to make finding, installing and updating plugins as easy as possible.

Note: The [underlying repository](https://github.com/Nudin/mpv-script-directory) of plugins is not (yet) complete, therefore not
all plugins can be installed automatically so far. Please help [filling it](https://github.com/Nudin/mpv-script-directory/blob/master/HOWTO_ADD_INSTALL_INSTRUCTIONS.md).

Installation
------------
You can install it via pip:
```
$ pip3 install mplug
```

Alternatively you can run it from the source:
- Install dependencies: python3, [GitPython](https://pypi.org/project/GitPython/)
- Clone this repository
- Run with `run.py`

Usage
-----
- You can find plugins in the WebUI of the [mpv script directory](https://nudin.github.io/mpv-script-directory/)
- To install a plugin `mplug install plugin_name`
- To update all plugins: `mplug upgrade`
- To upgrade database: `mplug update`
- To uninstall a plugin: `mplug uninstall plugin_id`
- To disable a plugin without uninstalling it: `mplug disable plugin_id`
- To search for a plugin `mplug search term`
- To list all installed plugins `mplug list-installed`

Status & Todo
-------------
- [X] Populate mpv script directory, by scraping wiki
- [X] First version of plugin manager
- [X] Write a Webinterface to browse plugins
- [ ] Add install instructions for **all** plugins to the [mpv script directory](https://github.com/Nudin/mpv-script-directory)
- [ ] Write a TUI?
- [ ] Write a GUI?
