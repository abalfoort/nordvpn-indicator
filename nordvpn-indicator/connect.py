#! /usr/bin/env python3

APPINDICATOR_ID = 'nordvpn-indicator'

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from os.path import abspath, dirname, join

# Local modules
from .nordvpn import get_countries, get_recommended_servers, \
                    get_recommended_country

# i18n: http://docs.python.org/3/library/gettext.html
import gettext
_ = gettext.translation(APPINDICATOR_ID, fallback=True).gettext


class NordVPNConnect(Gtk.Dialog):
    def __init__(self):
        # Paths
        self.script_dir = abspath(dirname(__file__))

    def show_connect(self):
        """
        Show connection dialog for NordVPN
        """
        Gtk.Dialog.__init__(self, title = _('NordVPN Connect'), parent = None, flags = 0)
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
        # Countries
        self.countries = get_countries()
        # Fill the countries combobox
        self.cmb_countries = Gtk.ComboBox.new()
        self.cmb_countries.set_hexpand(True)
        country_names = []
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
        grid.attach(self.cmb_servers, 1, grid_row, 1, 1)
        grid_row += 1
        
        # Pre-select country
        country = get_recommended_country()
        self.select_combobox_value(self.cmb_countries, country)
        
        # Show the window
        self.show_all()

        # Return country/server tuple
        response = self.run()
        connect_objs = (None, None)
        if response == Gtk.ResponseType.OK:
            country = self.get_selected_combobox_value(self.cmb_countries)
            server = self.get_selected_combobox_value(self.cmb_servers)
            connect_objs = (country, server)
        self.destroy()
        return connect_objs
        
    def get_country_id(self, country):
        """
        Returns the country code of a given country name.
        """
        for country_list in self.countries:
            if country_list[1] == country:
                return country_list[0]
        return 0

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
