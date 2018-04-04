# -*- coding: utf-8 -*-
import sys
from cx_Freeze import setup, Executable

options = {
	'build_exe':{
		'include_files':  ['config.ini'],
	}
}

executables = [
	Executable(
		script = "zabbix_get_graph.py", 
		base = "Console",
		icon = "img/zabbix.ico",
	)
]

setup(
    name = "Zabbix Get Graph",
    version = "1.0",
    description = "Utility for downloading graphs from Zabbix Frontend",
    options = options,
    executables = executables,
)
