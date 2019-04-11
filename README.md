Zabbix Get Graph
======================

Utility for downloading graphs from Zabbix Frontend.

Required
=======
* Zabbix 3.x, 4.0
* Python 3.x


Example
=======
Help
```console
user@localhost:~$ ./zabbix_get_graph.py -h
```
Config
```console
user@localhost:~$ nano config.ini
```
Run
```console
user@localhost:~$ ./zabbix_get_graph.py
[--] Starting: NetGraphs
[..] Time period:'2018-03-01 00:00:00' - '2018-03-31 23:59:59'
[OK] Graph id: 1043 saved: '/tmp/graphid_1043_enumerate_1.png'
[OK] Graph id: 1717 saved: '/tmp/graphid_1717_enumerate_2.png'
```

See also [wiki](http://wiki.enchtex.info/handmade/zabbix/zabbix_get_graph) page.
