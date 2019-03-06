#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------------------------------
import os
import re
import sys
import time
import datetime
from time import sleep
#
import argparse
import configparser
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import http.cookiejar
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


_SUPPORTED_ZABBIX_VERSIONS = ("3.0", "3.2", "3.4", "4.0")


def main():
    #__________________________________________________________________________
    # Входящие аргументы
    try:
        parser = argparse.ArgumentParser(description='Zabbix Get Graph - utility for downloading graphs from Zabbix Frontend')
        parser.add_argument("task", action='store', default=None, nargs='?', metavar='<TASK>',
                            help="specified task")
        parser.add_argument('--test', action='store_true', default=False, dest="test",
                            help="test mode")
        args = parser.parse_args()
    except SystemExit:
        return False
    #__________________________________________________________________________
    # Подключение config файла
    try:
        self_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        config_ini = configparser.ConfigParser()
        config_ini.read(os.path.join(self_dir, 'config.ini'))
    except Exception as err:
        print("[EE] Exception Err: {}".format(err), file=sys.stderr)
        print("[EE] Exception Inf: {}".format(sys.exc_info()), file=sys.stderr)
        return False
    if not config_ini.sections() or 'default' not in config_ini.sections():
        print("[EE] Configuration failed", file=sys.stderr)
        return False
    if not [x for x in config_ini.sections() if x != 'default']:
        print("[..] Nothing to do")
        return False
    #==============================================================================================
    #==============================================================================================
    # Start of the work cycle
    #==============================================================================================
    for task in [x for x in config_ini.sections() if x != 'default']:
        if args.task and task != args.task:
            continue
        print("[..] Working '{}'...".format(task))
        config_task = {
                'zabbix_version'    : "4.0",
                'zabbix_url'        : None,
                'zabbix_user'       : None,
                'zabbix_pass'       : None,
                'graphids'          : [],
                'time_from'         : None,
                'time_till'         : None,
                'img_widht'         : None,
                'img_height'        : None,
                'img_legend'        : True,
                'img_directory'     : None,
                'img_prefix'        : '',
            }
        ### default
        for x in config_task:
            try:
                config_task[x] = config_ini['default'][x] # <'str'>
            except KeyError:
                pass
            except Exception as err:
                print("[EE] Exception Err: {}".format(err), file=sys.stderr)
                print("[EE] Exception Inf: {}".format(sys.exc_info()), file=sys.stderr)
                return False
        ### task
        for x in config_task:
            try:
                config_task[x] = config_ini[task][x] # <'str'>
            except KeyError:
                pass
            except Exception as err:
                print("[EE] Exception Err: {}".format(err), file=sys.stderr)
                print("[EE] Exception Inf: {}".format(sys.exc_info()), file=sys.stderr)
                return False
        #______________________________________________________________________
        ### zabbix_version
        if config_task['zabbix_version'] not in _SUPPORTED_ZABBIX_VERSIONS:
            print("[EE] Unupported version", file=sys.stderr)
            return False
        ### graphids
        if not config_task['graphids']:
            print("[EE] Configuration failed: 'graphids'", file=sys.stderr)
            return False
        config_task['graphids'] = config_task['graphids'].strip().split()
        ### img_legend
        if isinstance(config_task['img_legend'], str):
            if config_task['img_legend'].lower() in ('0', 'false', 'off'):
                config_task['img_legend'] = False
            elif config_task['img_legend'].lower() in ('1', 'true', 'on'):
                config_task['img_legend'] = True
            else:
                print("[EE] Configuration failed: 'img_legend'", file=sys.stderr)
                return False
        ### img_prefix
        re_simple_str = re.compile("^([\w\-]*)$")
        if not re_simple_str.search(config_task['img_prefix']):
            print("[EE] Configuration failed: 'img_prefix'", file=sys.stderr)
            return False
        ### img_directory
        if not check_access_dir('rw', config_task['img_directory']):
            return False
        #______________________________________________________________________
        # time_period
        try:
            time_from = datetime.datetime.strptime(config_task['time_from'], "%Y/%m/%d %H:%M:%S")
            time_till = datetime.datetime.strptime(config_task['time_till'], "%Y/%m/%d %H:%M:%S")
            time_period = int((time_till - time_from).total_seconds())
        except Exception as err:
            print("[EE] Exception Err: {}".format(err), file=sys.stderr)
            print("[EE] Exception Inf: {}".format(sys.exc_info()), file=sys.stderr)
            return False
        #______________________________________________________________________
        # Authorization
        cj = http.cookiejar.CookieJar()
        # WARNING: without urlencode
        data = u"name={}&password={}&autologin=1&enter=Sign+in".format(config_task['zabbix_user'], config_task['zabbix_pass'])
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        opener.addheaders = [
            ('User-Agent',    'Zabbix Get Graph'),
            ('Content-Type',  'application/x-www-form-urlencoded'),
            ('Cache-Control', 'no-cache'),
            ]
        url = config_task['zabbix_url'].rstrip('/') + "/index.php"
        try:
            response = opener.open(url, data.encode('utf-8'), timeout=25)
        except Exception as err:
            print("[EE] Exception Err: {}".format(err), file=sys.stderr)
            print("[EE] Exception Inf: {}".format(sys.exc_info()), file=sys.stderr)
            return False
        #print(response.read()) #### TEST
        ### Проверка
        cookies = {}
        for cookie in cj:
            cookies[cookie.name] = cookie.value
        #print(cookies) #### TEST
        if 'zbx_sessionid' not in cookies:
            print("[EE] Authorization failed", file=sys.stderr)
            return False
        #______________________________________________________________________
        # Download
        print("[..] Time period: '{}' - '{}' ({}s)".format(time_from, time_till, time_period))
        for i, graphid in enumerate(config_task['graphids']):
            if config_task['img_prefix'] == "enumerate":
                img_file_name = "{}.png".format(i+1)
            else:
                img_file_name = "{}{}.png".format(config_task['img_prefix'], graphid)
            img_file_path = os.path.join(config_task['img_directory'], img_file_name)
            #__________________________________________________________________
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            url = config_task['zabbix_url'].rstrip('/')
            #
            if config_task['zabbix_version'] in ("3.0", "3.2", "3.4"):
                url += "/chart2.php?graphid={0}&profileIdx=web.graphs&profileIdx2={0}".format(graphid)
                url += "&stime={}&period={}&isNow=0".format(time_from.strftime("%Y%m%d%H%M%S"), time_period)
            else:
                url += "/chart2.php?graphid={0}&profileIdx=web.graphs.filter&profileIdx2={0}".format(graphid)
                url += "&from={}&to={}".format(time_from.strftime("%Y-%m-%d+%H:%M:%S"), time_till.strftime("%Y-%m-%d+%H:%M:%S"))
            #
            if config_task['img_widht']:
                url += "&width={}".format(config_task['img_widht'])
            if config_task['img_height']:
                url += "&height={}".format(config_task['img_height'])
            if not config_task['img_legend']:
                    url += "&legend=0"
            # TODO: &widget_view=0
            #__________________________________________________________________
            # Test mode
            if args.test:
                print("[..] {}".format(url))
                print("[..] -> {}".format(img_file_path))
                continue
            #__________________________________________________________________
            opener.addheaders = [
                ('User-Agent',    'Zabbix Get Graph'),
                ('Cache-Control', 'no-cache'),
                ]
            response = opener.open(url, timeout=25)
            content = response.read()
            ### Проверка
            #print response.code
            #print response.headers['content-type']
            #print content[0].encode('hex')
            #print(content[0])
            if response.code != 200 \
                or 'content-type' not in response.headers \
                or response.headers['content-type'] != 'image/png' \
                or (content[0]) != 137:
                    raise Exception('Download failed')
            #__________________________________________________________________
            # Save
            with open(img_file_path, 'wb') as f:
                f.write(content)
                print("[OK] Graph id:{} saved: '{}'".format(graphid, img_file_path), file=sys.stderr)
    #__________________________________________________________________________
    return True



#==================================================================================================
# Functions
#==================================================================================================
def check_access_dir(mode, *args):
    return_value = True
    modes_dict = {'ro': os.R_OK, 'rx': os.X_OK, 'rw': os.W_OK}
    for x in args:
        if not x:
            print("[EE] Directory is not specified", file=sys.stderr)
            return_value = False
            continue
        if os.path.exists(x):
            if os.path.isdir(x):
                if not os.access(x, modes_dict[mode]):
                    print("[EE] Access denied: '{}' ({})".format(x, mode), file=sys.stderr)
                    return_value = False
            else:
                print("[EE] Is not directory: '{}'".format(x), file=sys.stderr)
                return_value = False
        else:
            print("[EE] Does not exist: '{}'".format(x), file=sys.stderr)
            return_value = False
    #__________________________________________________________________________
    return return_value


def isfloat(self, str):
    try:
        float(str)
        return True
    except ValueError:
        return False


#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if __name__ == '__main__':
    rc = not main() # Compatible return code
    if os.name == 'nt':
        import msvcrt
        print("[..] Press any key to exit")
        msvcrt.getch()
    sys.exit(rc)
