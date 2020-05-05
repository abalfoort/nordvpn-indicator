#! /usr/bin/env python3

APPINDICATOR_ID = 'nordvpn-indicator'

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from os.path import abspath, dirname, join, exists
import subprocess

# i18n: http://docs.python.org/3/library/gettext.html
import gettext
from gettext import gettext as _
gettext.textdomain(APPINDICATOR_ID)


class NordVPNLogin(Gtk.Dialog):
    def __init__(self):
        # Paths
        self.script_dir = abspath(dirname(__file__))
        self.expect_template = join(self.script_dir, 'nordvpn-login.exp')
        # Return value
        self.value = (-1, '')

    def show(self):
        """
        Show login dialog for NordVPN
        """
        Gtk.Dialog.__init__(self, title = _('NordVPN Login'), parent = None, flags = 0)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)

        # Window settings
        self.set_resizable(False)
        self.connected_icon = join(self.script_dir, 'connected.svg')
        self.set_icon_from_file(self.connected_icon)
        self.set_position(Gtk.WindowPosition.MOUSE)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(350, -1)
        # Grid
        grid = Gtk.Grid()
        grid.set_row_spacing(5)
        grid.set_column_spacing(5)
        grid.set_margin_bottom(10)
        self.get_content_area().add(grid)
        # Add username label and entry field
        lbl_uname_ = Gtk.Label(_('Email'))
        lbl_uname_.set_halign(Gtk.Align.START)
        lbl_uname_.set_margin_left(5)
        grid.attach(lbl_uname_, 0, 0, 1, 1)
        self.txt_uname = Gtk.Entry()
        self.txt_uname.set_hexpand(True)
        grid.attach(self.txt_uname, 1, 0, 1, 1)
        # Add password label and entry field
        lbl_pwd = Gtk.Label(_('Password'))
        lbl_pwd.set_halign(Gtk.Align.START)
        lbl_pwd.set_margin_left(5)
        grid.attach(lbl_pwd, 0, 1, 1, 1)
        self.txt_pwd = Gtk.Entry()
        self.txt_pwd.set_visibility(False)
        self.txt_pwd.set_activates_default(True)
        self.txt_pwd.set_hexpand(True)
        grid.attach(self.txt_pwd, 1, 1, 1, 1)
        
        # Show the window
        self.show_all()
        response = self.run()
        if response == Gtk.ResponseType.OK:
            login = self.txt_uname.get_text().strip()
            password = self.txt_pwd.get_text().strip()
            if login and password:
                if exists(self.expect_template):
                    return_msg = ''
                    command = 'expect "{0}" "{1}" "{2}"'.format(self.expect_template, login, password)
                    return_code = subprocess.call(['bash', '-c', command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if return_code == 1: return_msg = 'ERROR: timeout'
                    elif return_code == 2: return_msg = 'ERROR: unexpected EOF'
                    elif return_code == 3: return_msg = 'ERROR: no login/password was given'
                    elif return_code > 3: return_msg = 'ERROR: unexpected error'
                    self.value = (return_code, return_msg)
                else:
                    self.value = (-1, _('Cannot find {}.'.format(self.expect_template)))
            else:
                self.value = (-1, _('Login/password was not given.'))
        self.destroy()
        return self.value
