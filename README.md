MPlug – a Plugin Manager for MPV
================================

A plugin manager for mpv to easy install and uninstall mpv scripts and more.

Installation
------------
- Install dependencies: python3, GitPython
- Clone this repository
- Run with `run.py`

Usage
-----
- To install a plugin `mplug install plugin_name`
- To update all plugins: `mplug upgrade`
- To upgrade database: `mplug update`
- To uninstall a plugin: `mplug uninstall plugin_id`
- To disable a plugin without uninstalling it: `mplug disable plugin_id`
- To search for a plugin `mplug search term`
- To list all installed plugins `mplug list-installed`
- You can find plugins in the WebUI of the [mpv script directory](https://nudin.github.io/mpv-script-directory/)

Status & Todo
-------------
- [X] Populate mpv script directory, by scraping wiki
- [X] First version of plugin manager
- [X] Write a Webinterface to browse plugins
- [ ] Add install instructions for all plugins to the [mpv script directory](https://github.com/Nudin/mpv-script-directory)
- [ ] Write a TUI
- [ ] Write a GUI
