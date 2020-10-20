#! /usr/bin/env python3

"""
NordVPN functions
Api examples: https://blog.sleeplessbeastie.eu/2019/02/18/how-to-use-public-nordvpn-api/
"""

import subprocess
from os.path import exists, join, \
                    abspath, dirname
from pathlib import Path
from glob import glob
import re

conf_path = '{0}/.config/nordvpn'.format(Path.home())
script_dir = abspath(dirname(__file__))

def nordvpn_connect(connect_object=''):
    """
    Connect to NordVPN.
    Argument: connect_object (string): country name, country abbreviation or server name
    """
    return _exec_con_command(['nordvpn', 'c', connect_object])

def nordvpn_disconnect():
    """
    Disconnect from NordVPN.
    """
    return _exec_con_command(['nordvpn', 'd'])

def _exec_con_command(command):
    """
    Called to connect or disconnect.
    Argument: command: list with commands/parameters
    """
    output = ''
    try:
        # Unfortunately, encoding='ansi' to filter out the ansi code is only supported from Python 3.6
        print('Execute command: {}'.format(' '.join(command)))
        output = subprocess.check_output(command, timeout=10).decode('utf-8').lower().strip()
        # Cleanup ansi
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        output = ansi_escape.sub('', output)
        print(('--------- exec_con_command ---------'))
        print(output)
        # Catch return non-errors:
        # We're having trouble reaching our servers. If the issue persists, please contact our customer support.
        # Whoops! We can't connect you to 'nl350.nordvpn.com'. Please try again. If the problem persists, contact our customer support.
        # Whoops! Cannot reach User Daemon.
        words = ['support', 'oops', 'cannot']
        return (2, output) if any(x in output for x in words) else (0, output)
    except subprocess.CalledProcessError as CPE:
        return (CPE.returncode, output)

def is_loggedin():
    """
    Check if we are logged into NordVPN.
    """
    # Use shell=True to return stdout and stderr together
    output = subprocess.check_output('LANG=C nordvpn login &', shell=True, timeout=2).decode('utf-8')
    return True if 'logged' in output else False

def get_connection_status():
    """
    Get connection status.
    """
    status = 'no_internet'
    command = "LANG=C nordvpn status | grep -i status: | awk '{print $NF}'"
    output = subprocess.check_output(command, shell=True).decode('utf-8').lower()
    if output:
        if 'discon' in output:
            status = 'disconnecting' if 'ing' in output else 'disconnected'
        else:
            status = 'connecting' if 'ing' in output else 'connected'
        if not exists(join(conf_path, 'has_account')):
            # Save an has_account file
            if status == 'connected':
                Path(join(conf_path, 'has_account')).touch()
    return status

def is_connected():
    """
    Check if we are connected to NordVPN.
    """
    return True if get_connection_status() == 'connected' else False

def needs_nordlynx():
    """
    Check if nordlynx is used.
    """
    command = 'LANG=C nordvpn settings | grep -i protocol'
    # Do not use stdout=PIPE or stderr=PIPE with subprocess.call.
    # The child process will block if it generates enough output to a pipe to fill up the OS pipe buffer as the pipes are not being read from.
    return_code = subprocess.call(command, shell=True)
    return False if return_code == 0 else True
    
def has_account():
    """
    Check if current user has an account.
    """
    if exists(join(conf_path, 'has_account')):
        return True
    elif is_loggedin():
        return True
    return False
    
def is_wireguard_installed():
    """
    Check if WireGuard is installed for NordLynx.
    """
    command = 'dpkg -l wireguard-dkms | grep ^ii'
    return_code = subprocess.call(command, shell=True)
    return True if return_code == 0 else False

def uses_nordlynx():
    """
    Check if nordlynx is used.
    """
    command = 'LANG=C nordvpn status | grep -i nordlynx'
    return_code = subprocess.call(command, shell=True)
    return True if return_code == 0 else False
    
def rate_connection(rate):
    """
    Rate the last connection.
    """
    if rate > 5: rate = 5
    if rate < 1: rate = 1
    print(('--------- rate_connection ---------'))
    print(('Previous connection rate: {0}'.format(rate)))
    command = 'LANG=C nordvpn rate {}'.format(rate)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    return_code = process.wait()
    return (return_code, process.stdout.read().decode('utf-8').replace('\r', '').replace('-', '').strip())

def get_fastest_server():
    """
    Get the fastest server
    """
    return get_recommended_servers()[0]
    
def get_countries():
    """
    Get a list of country ids, names and codes
    """
    countries = []
    try:
        output = subprocess.check_output(['nordvpn', 'countries'], timeout=5).decode('utf-8')
        output = output.replace('\r', '').replace('-', '').replace('_', ' ').strip()
        # Split on tabs, new lines and commas and remove empty strings from list (filter)
        nordvpn_countries = list(filter(None, sorted(re.split('\t|\n|, ', output))))
        command = "LANG=C curl --silent \"https://api.nordvpn.com/v1/servers/countries\" | jq --raw-output '.[] | [.id, .name, .code] | @tsv' 2>/dev/null | egrep -i '{0}'".format('|'.join(nordvpn_countries))
        print(('get_countries - public NordVPN API command: {0}'.format(command)))
        output = subprocess.check_output(command, shell=True, timeout=5).decode('utf-8')
        if output:
            # Split in lines
            output = output.split('\n')
            for line in output:
                # Split on tab
                country_list = line.split('\t')
                if len(country_list) == 3:
                    countries.append([int(country_list[0].strip()), country_list[1].replace(' ', '_'), country_list[2].lower()])
    except:
        pass
    return countries
    
def get_recommended_country():
    """
    Get country of fastest server
    Used to pre-select country in countries list
    """
    command = "LANG=C curl --silent \"https://api.nordvpn.com/v1/servers/recommendations\" | jq --raw-output 'first | .locations[].country.name'"
    print(('get_recommended_country - public NordVPN API command: {0}'.format(command)))
    try:
        return subprocess.check_output(command, shell=True, timeout=5).decode('utf-8').replace('\n', '')
    except:
        return ''
    
def get_account_info():
    """
    Get user account information
    """
    email = ''
    expires = ''
    try:
        output = subprocess.check_output(['nordvpn', 'account'], timeout=5).decode('utf-8').strip().split('\n')
        for line in output:
            if 'mail' in line.lower():
                email = line.split(':')[1].strip()
            elif 'expires' in line.lower():
                expires = line.split('(')[1].replace(')', '').strip()
                expires = 'Account {0}'.format(expires[0].lower() + expires[1:])
    except:
        pass
    return (email, expires)
    
def get_status_info():
    """
    Get status information
    """
    text = subprocess.check_output(['nordvpn', 'status'], timeout=5).decode('utf-8')
    return text.replace('\r', '').replace('-', '').strip()
    
def get_recommended_servers(country_code=-1):
    """
    Get recommended servers
    Argument: optional country code
    """
    filter = ''
    if country_code > -1:
        filter = '?filters\[country_id\]={0}'.format(country_code)
    # Get recommended servers
    if needs_nordlynx():
        command = "LANG=C curl -s 'https://api.nordvpn.com/v1/servers/recommendations{filter}' | jq --raw-output 'limit(10;.[]) | select(.load > 0) | select(.technologies[].identifier == \"wireguard_udp\") | .hostname' 2>/dev/null".format(filter=filter)
    else:
        command = "LANG=C curl -s 'https://api.nordvpn.com/v1/servers/recommendations{filter}' | jq --raw-output 'limit(10;.[]) | select(.load > 0) | .hostname' 2>/dev/null".format(filter=filter)
    print(('get_recommended_servers - public NordVPN API command: {0}'.format(command)))
    output = subprocess.check_output(command, shell=True, timeout=5).decode('utf-8').strip()
    # Init servers list
    servers = []
    lines = sorted(output.split())
    for line in lines:
        # Only keep the server name without nordvpn.com
        servers.append(line.split('.')[0])
    return servers
    
def load_order_page():
    """
    Get order page URL from ~/.config/nordvpn/indicator.conf
    Check for ORDER_LINK variable
    Then load order page in default browser
    """
    return_code = 1
    try:
        distro = get_distrib_id().upper()
        order_conf = join(conf_path, 'indicator.conf')
        config = get_config_dict(order_conf)
        order_url = config.get('ORDER_LINK', '')
        # If no order url was configured, save default in order_conf
        if not order_url:
            order_url = 'https://join.nordvpn.com/order/'
            with open(order_conf, 'w') as f:
                f.write('ORDER_LINK="{}"'.format(order_url))
        # Open url in browser
        if order_url:
            return_code = subprocess.call(['xdg-open', '{0}'.format(order_url)])
    except:
        return_code = 1
    return return_code

def get_distrib_id():
    """
    Get distribution ID from /etc/os-release or /etc/lsb-release
    """
    val = ''
    for f in glob('/etc/*release'):
        conf = get_config_dict(f)
        val = conf.get('ID', '')
        if not val:
            val = conf.get('DISTRIB_ID', '')
        if val: break
    return val

# Read keys from file
def get_config_dict(file, key_value=re.compile(r'^\s*(\w+)\s*=\s*["\']?(.*?)["\']?\s*(#.*)?$')):
    """
    Returns POSIX config file (key=value, no sections) as dict.
    Assumptions: no multiline values, no value contains '#'.
    """
    d = {}
    with open(file) as f:
        for line in f:
            try:
                key, value, _ = key_value.match(line).groups()
            except AttributeError:
                continue
            d[key] = value
    return d
