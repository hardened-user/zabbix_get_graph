#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------------------------------------------------
import argparse
import configparser
import datetime
import http.cookiejar
import os
import re
import ssl
import sys
import traceback
import urllib.error
import urllib.error
import urllib.parse
import urllib.parse
import urllib.request
import urllib.request

# noinspection PyProtectedMember
ssl._create_default_https_context = ssl._create_unverified_context

_SUPPORTED_ZABBIX_VERSIONS = ("3.0", "3.2", "3.4", "4.0")


def main():
    # __________________________________________________________________________
    # command-line options, arguments
    try:
        parser = argparse.ArgumentParser(
            description='Zabbix Get Graph - utility for downloading graphs from Zabbix Frontend')
        parser.add_argument("task", action='store', default=None, nargs='?',
                            metavar='<TASK>', help="specified task")
        parser.add_argument('--test', action='store_true', default=False,
                            help="test mode")
        args = parser.parse_args()
    except SystemExit:
        return False
    # __________________________________________________________________________
    # read configuration file
    try:
        self_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        config_ini = configparser.ConfigParser()
        config_ini.read(os.path.join(self_dir, 'config.ini'))
    except Exception as err:
        print("[!!] Unexpected Exception: {}\n{}".format(err, "".join(traceback.format_exc())))
        return False
    # __________________________________________________________________________
    if not [x for x in config_ini.sections() if x != 'default']:
        print("[..] Nothing to do", flush=True)
        return False
    # ==================================================================================================================
    # ==================================================================================================================
    # Start of the work cycle
    # ==================================================================================================================
    for task in [x for x in config_ini.sections() if x != 'default']:
        if args.task and task != args.task:
            continue
        print("[--] Starting: {}".format(task), flush=True)
        config_task = {
            'zabbix_version': "4.0",
            'zabbix_url': None,
            'zabbix_user': None,
            'zabbix_pass': None,
            'graphids': [],
            'time_from': None,
            'time_till': None,
            'img_name': "$ID",
            'img_width': None,
            'img_height': None,
            'img_legend': True,
            'img_directory': None
        }
        # config default
        for x in config_task:
            try:
                config_task[x] = config_ini['default'][x]  # <'str'>
            except KeyError:
                pass
            except Exception as err:
                print("[!!] Unexpected Exception: {}\n{}".format(err, "".join(traceback.format_exc())))
                return False
        # config task
        for x in config_task:
            try:
                config_task[x] = config_ini[task][x]  # <'str'>
            except KeyError:
                pass
            except Exception as err:
                print("[!!] Unexpected Exception: {}\n{}".format(err, "".join(traceback.format_exc())))
                return False
        # ______________________________________________________________________
        # zabbix_version
        if config_task['zabbix_version'] not in _SUPPORTED_ZABBIX_VERSIONS:
            print("[EE] Unsupported version: {}".format(config_task['zabbix_version']), flush=True)
            return False
        # graphids
        if not config_task['graphids']:
            print("[EE] Invalid value for argument: graphids", flush=True)
            return False
        config_task['graphids'] = config_task['graphids'].strip().split()
        # img_name
        re_simple_str = re.compile(r"^([\w\-$]*)$")
        if not re_simple_str.search(config_task['img_name']):
            print("[EE] Invalid value for argument: img_name", flush=True)
            return False
        # img_legend
        if isinstance(config_task['img_legend'], str):
            if config_task['img_legend'].lower() in ('0', 'false', 'off'):
                config_task['img_legend'] = False
            elif config_task['img_legend'].lower() in ('1', 'true', 'on'):
                config_task['img_legend'] = True
            else:
                print("[EE] Invalid value for argument: img_legend", flush=True)
                return False
        # img_directory
        if not fs_check_access_dir('rw', config_task['img_directory']):
            return False
        # time_period
        try:
            time_from = datetime.datetime.strptime(config_task['time_from'], "%Y/%m/%d %H:%M:%S")
            time_till = datetime.datetime.strptime(config_task['time_till'], "%Y/%m/%d %H:%M:%S")
            time_period = int((time_till - time_from).total_seconds())
        except Exception as err:
            print("[!!] Unexpected Exception: {}\n{}".format(err, "".join(traceback.format_exc())))
            return False
        # ______________________________________________________________________
        # Authorization
        cj = http.cookiejar.CookieJar()
        # WARNING: without urlencode
        data = u"name={}&password={}&autologin=1&enter=Sign+in".format(config_task['zabbix_user'],
                                                                       config_task['zabbix_pass'])
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        opener.addheaders = [
            ('User-Agent', 'Zabbix Get Graph'),
            ('Content-Type', 'application/x-www-form-urlencoded'),
            ('Cache-Control', 'no-cache'),
        ]
        url = config_task['zabbix_url'].rstrip('/') + "/index.php"
        try:
            # noinspection PyUnusedLocal
            response = opener.open(url, data.encode('utf-8'), timeout=29)
        except urllib.error.HTTPError as err:
            print("[EE] HTTP Exception: {}".format(err), flush=True)
            return False
        except Exception as err:
            print("[!!] Unexpected Exception: {}\n{}".format(err, "".join(traceback.format_exc())))
            return False
        # print(response.read()) #### TEST
        cookies = {}
        for cookie in cj:
            cookies[cookie.name] = cookie.value
        # print(cookies) #### TEST
        if 'zbx_sessionid' not in cookies:
            print("[EE] Authorization failed", flush=True)
            return False
        # ______________________________________________________________________
        # Download
        print("[..] Time period: '{}' - '{}' ({}s)".format(time_from, time_till, time_period), flush=True)
        for i, graphid in enumerate(config_task['graphids']):
            img_file_name = "{}.png".format(config_task['img_name'])
            img_file_name = img_file_name.replace("$ID", str(graphid))
            img_file_name = img_file_name.replace("$NUM", str(i + 1))
            img_file_path = os.path.join(config_task['img_directory'], img_file_name)
            # __________________________________________________________________
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            url = config_task['zabbix_url'].rstrip('/')
            #
            if config_task['zabbix_version'] in ("3.0", "3.2", "3.4"):
                url += "/chart2.php?graphid={0}&profileIdx=web.graphs&profileIdx2={0}".format(graphid)
                url += "&stime={}&period={}&isNow=0".format(time_from.strftime("%Y%m%d%H%M%S"), time_period)
            else:
                url += "/chart2.php?graphid={0}&profileIdx=web.graphs.filter&profileIdx2={0}".format(graphid)
                url += "&from={}&to={}".format(time_from.strftime("%Y-%m-%d+%H:%M:%S"),
                                               time_till.strftime("%Y-%m-%d+%H:%M:%S"))
            #
            if config_task['img_width']:
                url += "&width={}".format(config_task['img_width'])
            if config_task['img_height']:
                url += "&height={}".format(config_task['img_height'])
            if not config_task['img_legend']:
                url += "&legend=0"
            # TODO: &widget_view=0
            # __________________________________________________________________
            # Test mode
            if args.test:
                print("[..] {}".format(url), flush=True)
                print("[..] -> {}".format(img_file_path), flush=True)
                continue
            # __________________________________________________________________
            opener.addheaders = [
                ('User-Agent', 'Zabbix Get Graph'),
                ('Cache-Control', 'no-cache'),
            ]
            response = opener.open(url, timeout=25)
            content = response.read()
            if response.code != 200 \
                    or 'content-type' not in response.headers \
                    or response.headers['content-type'] != 'image/png' \
                    or content[0] != 137:
                # raise Exception(' failed')
                print("[EE] Download failed:\nHTTP status code: {}\n{}".format(
                    response.code,
                    '\n'.join(["{}: {}".format(x, response.headers[x]) for x in response.headers]), flush=True))
                return False
            # __________________________________________________________________
            # Save
            with open(img_file_path, 'wb') as f:
                f.write(content)
                print("[OK] Graph id: {} saved: '{}'".format(graphid, img_file_path), flush=True)
    # ==================================================================================================================
    # ==================================================================================================================
    # End of the work cycle
    # ==================================================================================================================
    # __________________________________________________________________________
    return True


# ======================================================================================================================
# Functions
# ======================================================================================================================
def fs_check_access_dir(mode, *args):
    """
    Directory permission check.
    """
    return_value = True
    modes = {'ro': os.R_OK, 'rx': os.X_OK, 'rw': os.W_OK}
    for x in args:
        if os.path.exists(x):
            if os.path.isdir(x):
                if not os.access(x, modes[mode]):
                    print("[EE] Directory access denied: {} ({})".format(x, mode), flush=True)
                    return_value = False
            else:
                print("[EE] Is not directory: {}".format(x), flush=True)
                return_value = False
        else:
            print("[EE] Directory does not exist: {}".format(x), flush=True)
            return_value = False
    # __________________________________________________________________________
    return return_value


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if __name__ == '__main__':
    rc = main()
    # __________________________________________________________________________
    if os.name == 'nt':
        # noinspection PyUnresolvedReferences
        import msvcrt

        print("[..] Press any key to exit", flush=True)
        msvcrt.getch()
    # __________________________________________________________________________
    sys.exit(not rc)  # Compatible return code
