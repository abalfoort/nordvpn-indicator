#! /usr/bin/env python3

"""
Dependencies: nordvpn, gir1.2-gtk-3.0, gir1.2-appindicator3-0.1
This script assumes successful login
Auto login with: nordvpn set autoconnect enabled [COUNTRY]
Get a list of countries with: nordvpn countries
"""

APPINDICATOR_ID = 'nordvpn-indicator'
INTERVAL = 10

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
except:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
gi.require_version('Notify', '0.7')

import subprocess
import signal
from threading import Event, Thread
from gi.repository import Notify
from os.path import abspath, dirname, join, exists
from pathlib import Path
import re
from os import makedirs

# Local modules
from .login import NordVPNLogin
from .connect import NordVPNConnect
from .settings import NordVPNSettings
from .nordvpn import is_loggedin, is_connected, get_fastest_server, \
                    has_account, load_order_page, get_account_info, \
                    get_status_info, get_connection_status, \
                    nordvpn_connect, nordvpn_disconnect, rate_connection

# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain(APPINDICATOR_ID)


class NordVPNIndicator():
    def __init__(self):
        """
        Provides tray icon with menu and checks
        every INTERVAL for changes in the connection.
        """
        # Save current directory
        self.script_dir = abspath(dirname(__file__))
        # Translations (used in multiple functions)
        self.order_text = _('Get a NordVPN account')
        self.connections = {
            'connecting': {'label': _('Quick connect'), 'icon': join(self.script_dir, 'connecting.svg')},
            'disconnecting': {'label': _('Quick connect'), 'icon': join(self.script_dir, 'connecting.svg')},
            'connected': {'label': _('Disconnect'), 'icon': join(self.script_dir, 'connected.svg')},
            'disconnected': {'label': _('Quick connect'), 'icon': join(self.script_dir, 'disconnected.svg')},
            'no_internet': {'label': _('Quick connect'), 'icon': join(self.script_dir, 'connecting.svg')}
        }
        self.manual_connect_text = _('Manual connect')
        self.status_text = _('Status Information')
        self.rate_text = _('Rate last connection')
        self.poor_text = _('poor')
        self.excellent_text = _('excellent')
        self.loggedin_text = _('You are not logged into NordVPN.\n'
                               'Please, login with: nordvpn login')
        
        self.current_connection = 'connecting'
        # Current NordVPN settings
        self.current_settings = {}
        self.fill_settings(True)
        self.settings_changed = False
        # Create event to use when thread is done
        self.check_done_event = Event()
        # Create indicator object
        self.indicator = AppIndicator3.Indicator.new(APPINDICATOR_ID, self.connections[self.current_connection]['icon'], AppIndicator3.IndicatorCategory.SYSTEM_SERVICES)
        self.indicator.set_title('NordVPN Indicator')
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())
        # Init notifier
        Notify.init(APPINDICATOR_ID)
        # Start thread to check for connection changes
        Thread(target=self.run_check).start()
        # Some debugging
        print(('--------- NordVPNIndicator Init ---------'))

    def fill_settings(self, force=False):
        """
        Get the current NordVPN settings in a dictionary
        You need to be logged in to get these settings
        """
        if force or self.settings_changed:
            settings = {'protocol': '', 'country': '', 'server': ''}
            try:
                output = subprocess.check_output(['nordvpn', 'settings']).decode('utf-8').lower().strip()
            except:
                output = ''
            if 'dns' in output:
                output = output.replace(' ', '').replace('-', '').replace('_', '')
                output_list = output.split('\n')
                for line in output_list:
                    # extract settings name and value
                    # DeprecationWarning: invalid escape sequence \w > mark the regex as raw string (prefix r)
                    match = re.search(r'([\w]+):([\w]+)', line)
                    if match:
                        value = match.group(2)
                        if 'enabled' in value: value = True
                        elif 'disabled' in value: value = False
                        settings[match.group(1)] = value
                # Add country details (because 'nordvpn settings' doesn't show it)
                nordvpn_save = '{}/.config/nordvpn'.format(str(Path.home()))
                if not exists(nordvpn_save): makedirs(nordvpn_save)
                settings['nordvpnsave'] = nordvpn_save
                if settings['autoconnect']:
                    server_save = join(nordvpn_save, 'server')
                    country_save = join(nordvpn_save, 'country')
                    if exists(server_save):
                        with open(server_save, 'r') as f:
                            settings['server'] = f.read().replace('\n', '').replace('\r', '')
                    elif exists(country_save):
                        with open(country_save, 'r') as f:
                            settings['country'] = f.read().replace('\n', '').replace('\r', '')

            # Save in the current_settings dictionary
            self.current_settings = settings
        # Show current settings
        print(('---------------- Settings ---------------'))
        print(("{}".format(', '.join("{!s}={!r}".format(key,val) for (key,val) in self.current_settings.items()))))

    def build_menu(self):
        """
        Build menu for the tray icon
        """
        menu = Gtk.Menu()
        if not has_account():
            self.item_order = Gtk.MenuItem.new_with_label(self.order_text)
            self.item_order.connect('activate', self.show_order_page)
            menu.append(self.item_order)
            menu.append(Gtk.SeparatorMenuItem())
        item_quick_connect = Gtk.MenuItem.new_with_label(self.connections[self.current_connection]['label'])
        item_quick_connect.connect('activate', self.quick_connect)
        menu.append(item_quick_connect)
        item_manual_connect = Gtk.MenuItem.new_with_label(self.manual_connect_text)
        item_manual_connect.connect('activate', self.manual_connect)
        menu.append(item_manual_connect)
        
        # Rating
        item_rate = Gtk.MenuItem.new_with_label(self.rate_text)
        sub_menu = Gtk.Menu()
        sub_item_rate_1 = Gtk.MenuItem.new_with_label('1 ({})'.format(self.poor_text))
        sub_item_rate_1.connect('activate', self.rate_prev_connection, 1)
        sub_menu.append(sub_item_rate_1)
        sub_item_rate_2 = Gtk.MenuItem.new_with_label('2')
        sub_item_rate_2.connect('activate', self.rate_prev_connection, 2)
        sub_menu.append(sub_item_rate_2)
        sub_item_rate_3 = Gtk.MenuItem.new_with_label('3')
        sub_item_rate_3.connect('activate', self.rate_prev_connection, 3)
        sub_menu.append(sub_item_rate_3)
        sub_item_rate_4 = Gtk.MenuItem.new_with_label('4')
        sub_item_rate_4.connect('activate', self.rate_prev_connection, 4)
        sub_menu.append(sub_item_rate_4)
        sub_item_rate_5 = Gtk.MenuItem.new_with_label('5 ({})'.format(self.excellent_text))
        sub_item_rate_5.connect('activate', self.rate_prev_connection, 5)
        sub_menu.append(sub_item_rate_5)
        item_rate.set_submenu(sub_menu)
        menu.append(item_rate)
        
        item_status = Gtk.MenuItem.new_with_label(self.status_text)
        item_status.connect('activate', self.show_status)
        menu.append(item_status)
        item_settings = Gtk.MenuItem.new_with_label(_('Settings'))
        item_settings.connect('activate', self.show_settings)
        menu.append(item_settings)
        menu.append(Gtk.SeparatorMenuItem())
        item_quit = Gtk.MenuItem.new_with_label(_('Quit'))
        item_quit.connect('activate', self.quit)
        menu.append(item_quit)
        menu.show_all()
        
        if self.current_connection == 'connecting' or \
           self.current_connection == 'disconnecting' or \
           self.current_connection == 'no_internet':
            # Connecting/disconnecting/no internet
            item_quick_connect.set_sensitive(False)
            item_manual_connect.set_sensitive(False)
            item_settings.set_sensitive(False)
            item_status.set_sensitive(False)
            item_rate.set_sensitive(False)
        elif self.current_connection == 'connected':
            # Connected
            item_quick_connect.set_sensitive(True)
            item_manual_connect.set_sensitive(False)
            item_settings.set_sensitive(True)
            item_status.set_sensitive(True)
            item_rate.set_sensitive(False)
        else:
            # Disconnected
            item_quick_connect.set_sensitive(True)
            item_manual_connect.set_sensitive(True)
            item_settings.set_sensitive(False)
            item_status.set_sensitive(True)
            item_rate.set_sensitive(True)
                
        return menu

    def run_check(self):
        """
        Checks every INTERVAL for changes in the connection.
        """
        while not self.check_done_event.is_set():
            connection = get_connection_status()
            if connection != self.current_connection:
                self.current_connection = connection
                print(('Connection status: {}'.format(self.current_connection)))
                # Change icon
                self.indicator.set_icon_full(self.connections[self.current_connection]['icon'], '')
                # Build menu
                self.indicator.set_menu(self.build_menu())
            self.check_done_event.wait(INTERVAL)

    def rate_prev_connection(self, widget, rate):
        """
        Rate the last connection
        """
        return_code, rate_result = rate_connection(rate)
        icon = 'dialog-ok'
        if return_code > 0:
            icon = 'dialog-error'
        # Show rate info in notification window
        Notify.Notification.new(self.rate_text, rate_result, icon).show()
    
    def show_status(self, widget=None):
        """
        Show a notification with status information
        of the current connection.
        """
        if is_connected():
            email, expires = get_account_info()
            # Use box horizontal character (dec 9472)
            text = '{0}\n{1}\n{2}'.format(expires, chr(9472) * 25, get_status_info())
            print(('-------------- show_status --------------'))
            print(text)
            icon = 'dialog-warning' if 'Disconnected' in text else 'dialog-information'
        else:
            text = self.loggedin_text
            icon = 'dialog-error'
        # Show status info in notification window
        Notify.Notification.new(self.status_text, text, icon).show()

    def show_settings(self, widget):
        """
        Show the settings window.
        """
        self.settings_changed = NordVPNSettings(self.current_settings).show_settings()
        self.fill_settings()
    
    def quick_connect(self, widget):
        """
        Quick connect.
        """
        self.change_connection(quick=True)
    
    def manual_connect(self, widget):
        """
        Show the connect window.
        """
        country, server = NordVPNConnect().show_connect()
        if country or server:
            self.change_connection(country=country, server=server)
        
    def show_order_page(self, widget=None):
        """
        Load the order page
        """
        load_order_page()

    def change_connection(self, country=None, server=None, connect=None, quick=False):
        """
        Start connection change in a thread
        Login when needed
        """
        return_code = 0
        if not is_loggedin():
            # Show login window
            return_code, last_line = NordVPNLogin().show()

        if return_code == 0:
            # Start this threaded or else the system tray icon does not change
            Thread(target=self.run_change_connection, kwargs={'country': country,'server': server, 'connect': connect, 'quick': quick}).start()
        else:
            # Failed to login
            title = _('Not logged into NordVPN.')
            Notify.Notification.new(title, last_line, 'dialog-error').show()
            print(('----------- change_connection -----------'))
            print(last_line)
            
    def run_change_connection(self, country=None, server=None, connect=None, quick=False):
        """
        Switches connection:
        Disconnect when connected and vise versa.
        """
        # Save current connection status
        if connect is None: connect = not is_connected()

        # Connect to country/server or disconnect
        connect_obj = ''
        if not quick and connect:
            if not country:
                country = self.current_settings['country']
            if not server:
                server = self.current_settings['server']
            connect_obj = server if server else country
            if not connect_obj:
                # Get fastest server to connect to
                connect_obj = get_fastest_server()

        if connect:
            return_code, output = nordvpn_connect(connect_obj)
        else:
            return_code, output = nordvpn_disconnect()
        # Show notification of error
        if return_code != 0:
            if not output:
                output = _('If the problem persists, contact NordVPN customer support.')
            error_title = _('Failed to connect to "{0}"'.format(connect_obj)) if connect else _('Failed to disconnect from "{0}"'.format(connect_obj))
            Notify.Notification.new(error_title, output, 'dialog-error').show()

    def quit(self, widget=None):
        """
        Quit the application.
        """
        self.check_done_event.set()
        Notify.uninit()
        Gtk.main_quit()

def main():
    NordVPNIndicator()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()
    
if __name__ == '__main__':
    main()
