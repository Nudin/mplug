MPlug – a pluding manager for mpv
=================================

A plugin manager for mpv to easy install and uninstall mpv scripts and more.

Install and usage
-----------------
- Install dependencies: python3, GitPython
- Clone this repository
- Run mplug
	- To install a plugin `./mplug install plugin_name`
	- To update all plugins: `./mplug upgrade`
	- To upgrade database: `./mplug update`
	- To uninstall a plugin: `./mplug uninstall plugin_id`
	- To disable a plugin without uninstalling it: `./mplug disable plugin_id`

Status & Todo
-------------
- [Done] Populate mpv script directory, by scraping wiki
- [Done] First version of plugin manager
- [WIP] Add install instructions to mpv scraping directory
- [TODO] Add Tests and clean up code
- [TODO] Write a Webinterface to browse plugins
- [TODO] Write a TUI
- [TODO] Write a GUI
