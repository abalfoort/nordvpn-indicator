#! /usr/bin/env python3

APPINDICATOR_ID = 'nordvpn-indicator'

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from os.path import abspath, dirname, join, exists
from os import remove
import subprocess
from nordvpn import get_countries, get_recommended_servers, \
                    is_wireguard_installed, uses_nordlynx, \
                    get_fastest_server, conf_path

# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain(APPINDICATOR_ID)


class NordVPNSettings(Gtk.Dialog):
    def __init__(self, current_settings):
        # Paths
        self.script_dir = abspath(dirname(__file__))
        # Current NordVPN settings
        self.current_settings = current_settings

    def show_settings(self):
        """
        Show settings dialog for NordVPN
        """
        Gtk.Dialog.__init__(self, title = _('NordVPN Settings'), parent = None, flags = 0)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)

        # Window settings 
        self.set_resizable(False)
        self.connected_icon = join(self.script_dir, 'connected.svg')
        self.set_icon_from_file(self.connected_icon)
        self.set_position(Gtk.WindowPosition.MOUSE)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(400, -1)
        # Grid
        grid = Gtk.Grid()
        grid.set_row_spacing(5)
        grid.set_column_spacing(5)
        grid.set_margin_bottom(10)
        self.get_content_area().add(grid)
        # Autoconnect
        self.chk_autoconnect = Gtk.CheckButton()
        self.chk_autoconnect.connect('toggled', self.on_chk_autoconnect_toggled)
        self.chk_autoconnect.set_label(_('Auto Connect'))
        self.chk_autoconnect.set_tooltip_text(_('Automatically connect to NordVPN on login.\n'
                                                'You can optionally select a country or a recommended server.'))
        grid.attach(self.chk_autoconnect, 0, 0, 1, 1)
        # Countries
        self.countries = get_countries()
        # Fill the countries combobox
        self.cmb_countries = Gtk.ComboBox.new()
        self.cmb_countries.set_hexpand(True)
        country_names = ['']
        grid_row = 0
        for country_list in self.countries:
            # Create list with only country names for the combobox
            country_names.append(country_list[1])
        self.fill_combobox(self.cmb_countries, country_names)
        self.cmb_countries.connect('changed', self.on_cmb_country_changed)
        grid.attach(self.cmb_countries, 1, grid_row, 1, 1)
        grid_row += 1
        # Country servers
        self.cmb_servers = Gtk.ComboBox.new()
        self.cmb_servers.set_hexpand(True)
        # Get recommended servers
        #self.on_cmb_country_changed()
        grid.attach(self.cmb_servers, 1, grid_row, 1, 1)
        grid_row += 1
        # Cybersec
        self.chk_cybersec = Gtk.CheckButton()
        self.chk_cybersec.set_label(_('Cyber Security'))
        self.chk_cybersec.set_tooltip_text(_('Automatically block suspicious websites\n'
                                             'and block advertisements.'))
        grid.attach(self.chk_cybersec, 0, grid_row, 1, 1)
        grid_row += 1
        # Killswitch
        self.chk_killswitch = Gtk.CheckButton()
        self.chk_killswitch.set_label(_('Kill Switch'))
        self.chk_killswitch.set_tooltip_text(_('Disable system-wide internet access\n'
                                               'if the VPN connection suddenly disconnects.'))
        grid.attach(self.chk_killswitch, 0, grid_row, 1, 1)
        grid_row += 1
        # Protocol (not for NordLynx)
        if self.current_settings['protocol']:
            lbl_protocol = Gtk.Label(_('Protocol'))
            lbl_protocol.set_halign(Gtk.Align.START)
            lbl_protocol.set_margin_left(5)
            grid.attach(lbl_protocol, 0, grid_row, 1, 1)
            self.cmb_protocol = Gtk.ComboBox.new()
            self.cmb_protocol.set_hexpand(True)
            self.fill_combobox(self.cmb_protocol, ['UDP', 'TCP'])
            grid.attach(self.cmb_protocol, 1, grid_row, 1, 1)
            grid_row += 1
        # NordLynx - check if wireguard is installed
        self.show_nordlynx = is_wireguard_installed()
        if self.show_nordlynx:
            self.chk_nordlynx = Gtk.CheckButton()
            self.chk_nordlynx.set_label(_('NordLynx'))
            self.chk_nordlynx.set_tooltip_text(_('Use NordLynx instead of OpenVPN.\n'
                                                 'Deselect to use the default OpenVPN.'))
            grid.attach(self.chk_nordlynx, 0, grid_row, 1, 1)
            grid_row += 1
        # Logs
        lbl_logs = Gtk.Label(label=_('Logs'))
        lbl_logs.set_halign(Gtk.Align.START)
        lbl_logs.set_margin_start(5)
        grid.attach(lbl_logs, 0, grid_row, 1, 1)
        btn_viewlogs = Gtk.Button.new_with_label(_('View Logs'))
        btn_viewlogs.set_hexpand(True)
        btn_viewlogs.connect("clicked", self.on_btn_viewlogs_clicked)
        grid.attach(btn_viewlogs, 1, grid_row, 1, 1)

        # Pre-select from self.current_settings:
        # dns=False, nordvpnsave='/home/arjen/.config/nordvpn', country='', autoconnect=True, protocol='', cybersec=True, notify=True, server='', killswitch=False
        if self.current_settings['autoconnect']:
            self.chk_autoconnect.set_active(True)
            if self.current_settings['server']:
                # If a server is configured for auto-connect, select country from server name
                server_country = self.get_country_by_code(self.current_settings['server'][0:2])
                self.select_combobox_value(self.cmb_countries, server_country)
                self.select_combobox_value(self.cmb_servers, self.current_settings['server'])
            else:
                # Country is configured for auto-connect
                self.select_combobox_value(self.cmb_countries, self.current_settings['country'])
        if self.current_settings['cybersec']: self.chk_cybersec.set_active(True)
        if self.current_settings['killswitch']: self.chk_killswitch.set_active(True)
        
        # NordVPN can use openVPN and NordLynx
        # NordLynx does not set protocol (UDP only)
        self.nordlynx_selected = False
        if self.current_settings['protocol']:
            self.select_combobox_value(self.cmb_protocol, self.current_settings['protocol'].upper())
        elif self.show_nordlynx:
            self.nordlynx_selected = uses_nordlynx()
            self.chk_nordlynx.set_active(self.nordlynx_selected)
        
        # Show the window
        self.show_all()

        # Handle user response
        response = self.run()
        settings_changed = False
        if response == Gtk.ResponseType.OK:
            settings_changed = self.save_settings()
        self.destroy()
        return settings_changed
        
    def on_btn_viewlogs_clicked(self, widget):
        """
        Open log files if they exist
        """
        logs = ['/var/log/nordvpn/daemon.log', 
                '{0}/indicator.log'.format(conf_path)]
        for log in logs:
            if exists(log):
                subprocess.call('xdg-open {}'.format(log), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def get_country_id(self, country):
        """
        Returns the country id of a given country name.
        """
        for country_list in self.countries:
            if country_list[1] == country:
                return country_list[0]
        return 0
        
    def get_country_code(self, country):
        """
        Returns the country code of a given country name.
        """
        for country_list in self.countries:
            if country_list[1] == country:
                return country_list[2]
        return ''
        
    def get_country_by_code(self, country_code):
        """
        Returns the country name by a given country code.
        """
        country_code = country_code.lower()
        for country_list in self.countries:
            if country_list[2] == country_code:
                return country_list[1]
        return ''

    def fill_combobox(self, combobox, data_list, selected_index=None):
        """
        Returns a Gtk.ComboBox object from a data list.
        
        Arguments: Gtk.ComboBox object, a data list, optional selected index (0+).
        """
        if combobox is None:
            return

        try:
            liststore = combobox.get_model()
            liststore.clear()
        except:
            liststore = Gtk.ListStore(str)
            cell = Gtk.CellRendererText()
            combobox.pack_start(cell, True)
            combobox.add_attribute(cell, "text", 0)

        for data in data_list:
            liststore.append([str(data)])
        combobox.set_model(liststore)
        
        if selected_index:
            combobox.set_active(selected_index)

    def get_selected_combobox_value(self, combobox):
        """
        Returns the currently selected of a Gtk.Combobox.
        
        Arguments: Gtk.ComboBox object.
        """
        active_iter = combobox.get_active_iter()
        if active_iter is not None:
            return combobox.get_model().get_value(active_iter, 0)
        return ''

    def select_combobox_value(self, combobox, value):
        """
        Selects a value of a Gtk.Combobox.
        
        Arguments: Gtk.ComboBox object, value to select.
        """
        i = 0
        liststore = combobox.get_model()
        if liststore is not None:
            for data in liststore:
                if data[0] == value: break
                i += 1
            combobox.set_active(i)

    def on_chk_autoconnect_toggled(self, widget):
        """
        Enables/disables the country/server Gtk.ComboBox when
        the autoconnect Gtk.Checkbutton is toggled.
        """
        if widget.get_active():
            if self.current_settings['server']:
                self.select_combobox_value(self.cmb_servers, self.current_settings['server'])
            else:
                self.select_combobox_value(self.cmb_countries, self.current_settings['country'])
            self.cmb_servers.set_sensitive(True)
            self.cmb_countries.set_sensitive(True)
        else:
            self.cmb_countries.set_active(0)
            self.cmb_countries.set_sensitive(False)
            self.cmb_servers.set_active(0)
            self.cmb_servers.set_sensitive(False)
            
    def on_cmb_country_changed(self, widget=None):
        """
        Display recommended servers
        """
        country = self.get_selected_combobox_value(self.cmb_countries)
        if country:
            # Get recommended servers for selected country
            servers = get_recommended_servers(self.get_country_id(country))
            # Add an empty string at the beginning of the list
            servers.insert(0, '')
            # Fill combobox
            self.fill_combobox(self.cmb_servers, servers, 1)
        else:
            # Clear server comobox
            self.fill_combobox(self.cmb_servers, [])

    def save_settings(self):
        """
        Save the settings.
        """
        settings_changed = False
        # Get settings
        country = self.get_selected_combobox_value(self.cmb_countries)
        server = self.get_selected_combobox_value(self.cmb_servers)
        country_save = join(self.current_settings['nordvpnsave'], 'country')
        server_save = join(self.current_settings['nordvpnsave'], 'server')
        if exists(country_save): remove(country_save)
        if exists(server_save): remove(server_save)
        autoconnect = self.chk_autoconnect.get_active()
        if autoconnect:
            if server:
                with open(server_save, 'w') as f:
                    f.write(server)
                if exists(country_save): remove(country_save)
            elif country:
                with open(country_save, 'w') as f:
                    f.write(country)
                if exists(server_save): remove(server_save)
            
        cybersec = self.chk_cybersec.get_active()
        killswitch = self.chk_killswitch.get_active()
        
        protocol = ''
        nordlynx = None
        if self.current_settings['protocol']:
            protocol = self.get_selected_combobox_value(self.cmb_protocol)
        if self.show_nordlynx:
            nordlynx = self.chk_nordlynx.get_active()

        # Execute the commands
        if self.current_settings['autoconnect'] != autoconnect or \
           self.current_settings['server'] != server or  \
           self.current_settings['country'] != country:
            connect_obj = server if server else country
            command = 'nordvpn set autoconnect disabled; nordvpn set autoconnect enabled {}'.format(connect_obj) if autoconnect else 'nordvpn set autoconnect disabled'
            print('Execute command: {}'.format(command))
            return_code = subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if return_code == 0: settings_changed = True 
        if self.current_settings['cybersec'] != cybersec:
            command = 'nordvpn set cybersec enabled' if cybersec else 'nordvpn set cybersec disabled'
            print('Execute command: {}'.format(command))
            return_code = subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if return_code == 0: settings_changed = True 
        if self.current_settings['killswitch'] != killswitch:
            command = 'nordvpn set killswitch enabled' if killswitch else 'nordvpn set killswitch disabled'
            print('Execute command: {}'.format(command))
            return_code = subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if return_code == 0: settings_changed = True 
        if self.current_settings['protocol'] != protocol.lower():
            command = 'nordvpn set protocol {}'.format(protocol).split()
            print('Execute command: {}'.format(command))
            return_code = subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if return_code == 0: settings_changed = True 
        if nordlynx is not None:
            if nordlynx != self.nordlynx_selected:
                command = 'nordvpn d; nordvpn set technology OpenVPN; nordvpn c {}'.format(get_fastest_server())
                if nordlynx:
                    command = 'nordvpn d; nordvpn set technology NordLynx; nordvpn c {}'.format(get_fastest_server())
                print('Execute command: {}'.format(command))
                return_code = subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if return_code == 0: settings_changed = True 
        return settings_changed
