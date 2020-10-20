---
layout: page
title: NORDVPN-INDICATOR
section: 1
footer: "NordVPN Indicator"
header: "NordVPN Indicator"
date: September 2020
---

# NAME

nordvpn-indicator - Linux system tray icon for nordvpn

# SYNOPSIS

**nordvpn-indicator** \[**-d**|**--debug**]

# DESCRIPTION

NordVPN Indicator sits in the system tray and shows the
user the status of the NordVPN connection:

 1. Red: not connected.
 2. Blue: connected.
 3. Grey: connecting.

Right-click to open the menu:

 1. Connect the fastest server or select a server manually.
 2. Change settings.
 3. Show status information.
 4. Value the last used connection.

-d, --debug
:   Prints debug information.


# FILES

~/.config/nordvpn/indicator.log
:   Per-user log file.

~/.config/nordvpn/has_account
:   Indicator file to flag that the user has an account.

~/.config/nordvpn/indicator.conf
:   Optional configuration file.

# Author

Written by Arjen Balfoort

# BUGS

https://gitlab.com/abalfoort/nordvpn-indicator/-/issues


