#!/usr/bin/env python

#	gcwconnect.py
#
#	Requires: pygame, urllib, json
#
#	Copyright (c) 2013-2020 Hans Kokx
#
#	Licensed under the GNU General Public License, Version 3.0 (the "License");
#	you may not use this file except in compliance with the License.
#	You may obtain a copy of the License at
#
#	http://www.gnu.org/copyleft/gpl.html
#
#	Unless required by applicable law or agreed to in writing, software
#	distributed under the License is distributed on an "AS IS" BASIS,
#	WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#	See the License for the specific language governing permissions and
#	limitations under the License.

import json
import os
import shutil
import subprocess as SU
import sys
import time
from os import listdir
from urllib import parse

import pygame
import pygame.gfxdraw
from pygame.locals import *

# What is our wireless interface?
wlan = "wlan0"

# What is our screen resolution?
screen_width = 320
screen_height = 240

###############################################################################
#                                                                             #
#                             Global variables                                #
#                                                                             #
###############################################################################
selected_key = ''
passphrase = ''
active_menu = ''

colors = {
    "darkbg":           (41, 41, 41),
    "lightbg":          (84, 84, 84),
    "activeselbg":      (160, 24, 24),
    "inactiveselbg":    (84, 84, 84),
    "activetext":       (255, 255, 255),
    "inactivetext":     (128, 128, 128),
    "lightgrey":        (200, 200, 200),
    "logogcw":          (255, 255, 255),
    "logoconnect":      (216, 32, 32),
    "yellow":           (128, 128, 0),
    "blue":             (0, 0, 128),
    "red":              (128, 0, 0),
    "green":            (0, 128, 0),
    "black":            (0, 0, 0),
    "white":            (255, 255, 255),
}



mac_addresses = {}

###############################################################################
#                                                                             #
#                       Application initialization                            #
#                                                                             #
###############################################################################

class Display:
    """Creates a PyGame display for the application to draw on.
    """
    def __init__(self):
        # Initialize the display, for pygame
        self.surface = pygame.display.set_mode((screen_width, screen_height))

        if not pygame.display.get_init():
            pygame.display.init()
        if not pygame.font.get_init():
            pygame.font.init()

        self.surface.fill(colors["darkbg"])
        pygame.mouse.set_visible(False)
        pygame.key.set_repeat(199, 69)  # (delay,interval)

    def update():
        pygame.display.update()

    def draw_scrim(self):
        """Draws a tranclucent background over the display.
        """        
        # A scrim for the background of the Modal
        self.scrim = pygame.Surface((screen_width, screen_height))
        self.scrim.fill((0, 0, 0))
        self.scrim.set_alpha(128)
        self.surface.blit(self.scrim, (0, 0))

    def remove_scrim(self):
        """Removes the scrim from the display.
        """        
        if self.scrim:
            self.scrim.remove()

class Font:
    def __init__(self):
        """Configures the fonts for the application to use
        """
        # Fonts
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        try:
            pygame.font.Font(font_path, 10)
        except:
            font_path = os.environ['HOME'] + \
                '\\AppData\\Local\\Microsoft\\Windows\\Fonts\\DejaVuSans.ttf'

        self.font_tiny = pygame.font.Font(font_path, 8)
        self.font_small = pygame.font.Font(font_path, 10)
        self.font_medium = pygame.font.Font(font_path, 12)
        self.font_large = pygame.font.Font(font_path, 16)
        self.font_huge = pygame.font.Font(font_path, 48)

        self.font_mono_path = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
        try:
            pygame.font.Font(self.font_mono_path, 10)
        except:
            self.font_mono_path = os.environ['HOME'] + \
                '\\AppData\\Local\\Microsoft\\Windows\\Fonts\\DejaVuSansMono.ttf'
        self.font_mono_small = pygame.font.Font(self.font_mono_path, 11)

class Configuration(ssid = None, passphrase = None):
    def __init__(self):
        """Define and create configuration paths, then convert "old style" configuration files into "new style" configuration files.
        """
        self.confdir = os.environ['HOME'] + "/.local/share/gcwconnect/"
        self.netconfdir = self.confdir+"networks/"
        self.sysconfdir = "/usr/local/etc/network/"
        self.datadir = "/usr/share/gcwconnect/"

        if not os.path.exists(self.datadir):
            self.datadir = "data/"
        if not os.path.exists(self.confdir):
            os.makedirs(self.confdir)
        if not os.path.exists(self.netconfdir):
            os.makedirs(self.netconfdir)
        if not os.path.exists(self.sysconfdir):
            os.makedirs(self.sysconfdir)

        """
        In the directory containing WiFi network configuration files, removes
        backslashes from file names created by older versions of GCW Connect.
        """
        try:
            confNames = listdir(self.netconfdir)
        except IOError as ex:
            print("Failed to list files in '%s': %s", (self.netconfdir, ex))
        else:
            for confName in confNames:
                if not confName.endswith('.conf'):
                    continue
                if '\\' in confName:
                    old, new = confName, parse.quote_plus(
                        confName.replace('\\', ''))
                    try:
                        os.rename(os.path.join(self.netconfdir, old),
                                os.path.join(self.netconfdir, new))
                    except IOError as ex:
                        print("Failed to rename old-style network configuration file '%s' to '%s': %s" % (
                            os.path.join(self.netconfdir, old), new, ex))

    def write(self):
        """
        Write a configuration file to disk

        Args:
            ssid (str): The SSID to write a configuration file for
        """

        conf = self.netconfdir + parse.quote_plus(self.ssid) + ".conf"

        f = open(conf, "w")
        f.write('WLAN_ESSID="' + ssid + '"\n')

        # FIXME: SSIDs with special characters should be converted to hex, per this example:
        #
        #    # Special characters in SSID, so use hex string. Default to WPA-PSK, WPA-EAP
        #    # and all valid ciphers.
        #    network={
        #        ssid=00010203
        #        psk=000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
        #    }
        #
        # It looks like this should do the trick:
        #
        #   for character in string:
        #       print(character, character.encode('utf-8').hex())

        if len(self.passphrase) > 0 and self.passphrase != "none":
            f.write('WLAN_PASSPHRASE="'+self.passphrase+'"\n')
            f.write('WLAN_ENCRYPTION="wpa2"\n')  # Default to WPA2

            # FIXME: People might want WPA-1 or WEP. Right now, we don't know of a way to determine the type of encryption on a given network. Ideally, we would have a to determine the type of encryption, and write the configuration file in a way that is appropriate for that.  However, the following note may help if it is used to update `wlan-config`:

            ############################################################################
            #                                   NOTE                                   #
            ############################################################################
            #    https://w1.fi/cgit/hostap/plain/wpa_supplicant/wpa_supplicant.conf    #
            #                                                                          #
            # Catch all example that allows more or less all configuration modes       #
            #        network = {                                                       #
            #            ssid = "example"                                              #
            #            scan_ssid = 1                                                 #
            #            key_mgmt = WPA-EAP WPA-PSK IEEE8021X NONE                     #
            #            pairwise = CCMP TKIP                                          #
            #            group = CCMP TKIP WEP104 WEP40                                #
            #            psk = "very secret passphrase"                                #
            #            eap = TTLS PEAP TLS                                           #
            #            identity = "user@example.com"                                 #
            #            password = "foobar"                                           #
            #            ca_cert = "/etc/cert/ca.pem"                                  #
            #            client_cert = "/etc/cert/user.pem"                            #
            #            private_key = "/etc/cert/user.prv"                            #
            #            private_key_passwd = "password"                               #
            #            phase1 = "peaplabel=0"                                        #
            #        }                                                                 #
            ############################################################################

        elif self.passphrase == "none":   # Unencrypted network
            f.write('WLAN_ENCRYPTION="none"\n')
        f.close()

    def get_saved_key(self):
        """
        Retreive the network key from a saved configuration file

        Args:
            ssid (str): The SSID of the network to retrieve the key for

        Returns:
            str: The unencrypted network key for the given SSID
        """
        key = None
        conf = self.netconfdir + parse.quote_plus(self.ssid) + ".conf"
        output = open(conf, "r")
        if output is not None:
            for line in output:
                if line.strip().startswith('WLAN_PASSPHRASE'):
                    key = str(line.strip().split("=")[1])[1:-1]

        return key

    def get_saved_networks():
        """Get a list of all configured networks which are saved on disk.

        Returns:
            dict: A dictionary of all network configurations which are saved on disk, including the SSID ("ESSID") and passphrase ("Key").
        """
        saved_network = {}
        index = 0
        for confName in sorted(listdir(configuration.netconfdir), reverse=True):
            if not confName.endswith('.conf'):
                continue
            ssid = parse.unquote_plus(confName[:-5])

            detail = {
                'ESSID': ssid,
                'Key': ''
            }
            try:
                with open(configuration.netconfdir + confName) as f:
                    for line in f:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                            value = value[1:-1]
                        if key == 'WLAN_ESSID':
                            detail['ESSID'] = value
                        elif key == 'WLAN_PASSPHRASE':
                            detail['Key'] = value
            except IOError as ex:
                print('Error reading conf:', ex)
                pass
            except ValueError as ex:
                print('Error parsing conf')
                pass
            else:
                saved_network[index] = detail
                index += 1

        return saved_network

class Interface():

    def stop(self):
        """
        Disconnect from wifi and/or bring down the hosted AP

        Returns:
            bool/str: Returns a string with the status of the connection, False if not connected
        """
        try:
            SU.Popen(['sudo', '/sbin/ap', '--stop'], close_fds=True).wait()
        except:
            pass

        try:
            SU.Popen(['sudo', '/sbin/ifdown', wlan], close_fds=True).wait()
        except:
            pass

        status = self.status()
        return status

    def start(self):
        """
        Try to connect the wlan interface to wifi

        Returns:
            bool/str: Returns a string with the status of the connection, False if not connected
        """

        SU.Popen(['sudo', '/sbin/ifup', wlan], close_fds=True).wait() == 0

        status = self.status()
        return status

    def enable(self):
        """
        Enables the wlan interface.

        Returns:
            bool: Returns False if the interface was previously enabled, otherwise returns True
        """
        check = self.status()
        if check is not False:
            return False

        modal = Modal(text="Enabling WiFi...")
        modal.show()

        while True:
            if SU.Popen(['sudo', '/sbin/ip', 'link', 'set', wlan, 'up'],
                        close_fds=True).wait() == 0:
                break
            time.sleep(0.1)
        modal.clear()
        return True

    def disable():
        """
        Disables the wlan interface
        """

        modal = Modal("Disabling WiFi...")
        modal.show()
        while True:
            if SU.Popen(['sudo', '/sbin/ip', 'link', 'set', wlan, 'down'],
                        close_fds=True).wait() == 0:
                break
            time.sleep(0.1)
        modal.clear()

    def check_if_dormant():
        """
        Cheecks if the wlan interface is dormant

        Returns:
            bool: False if the interface is dormant, otherwise True.
        """

        try:
            with open("/sys/class/net/" + wlan + "/dormant", "rb") as state:
                return state.readline().decode("utf-8").strip()
        except IOError:
            return False  # WiFi is disabled

    def status(self):
        """
        Determine the status of the wlan interface and its connection state.

        Returns:
            bool/str: Returns a str containing the interface status or False if interface is down
        """
        interface_status = False

        interface_is_up = self.check_if_dormant()
        connected_to_network = self.network.ssid()
        ip_address = self.address.ip()
        ap_is_broadcasting = self.ap.status()

        if ap_is_broadcasting:
            interface_status = "Broacasting"
        else:
            if interface_is_up != False:
                interface_status = "Up"
                if connected_to_network is not None:
                    interface_status = "Associated"
                    if ip_address is not None:
                        interface_status = "Connected"
        return interface_status

###############################################################################
#                                                                             #
#              Hardware address, IP address, and SSID grabbers                #
#                                                                             #
###############################################################################

class Address:

    def ip():
        """
        Determine the IP address of the wlan interface. Ignores 169.254.x.x addresses.

        Returns:
            str: The IP address of the interface, or None if unavailable.
        """
        ip = None
        try:
            with open(os.devnull, "w") as fnull:
                output = SU.Popen(['/sbin/ip', '-4', 'a', 'show', wlan],
                                stderr=fnull, stdout=SU.PIPE, close_fds=True).stdout.readlines()

            for line in output:
                line = line.decode("utf-8").strip()
                if line.startswith("inet"):
                    tmp = line.split()[1].split("/")[0]
                    if not tmp.startswith("169.254"):
                        ip = tmp
        except:
            ip = None
        return ip

    def mac():
        """
        Acquire the wlan MAC address

        Returns:
            bool/str: Returns the wlan MAC address, or False if the interface is disabled
        """
        try:
            with open("/sys/class/net/" + wlan + "/address", "rb") as mac_file:
                return mac_file.readline(17).decode("utf-8").strip()
        except IOError:
            return False  # WiFi is disabled

class Network():

    def ssid(self):
        """
        Determine which SSID the device is currently associated with

        Returns:
            str: Returns the SSID of the network currently associated with; otherwise returns None if no network is associated.
        """
        ssid = None
        is_broadcasting_ap = self.ap.status()
        try:
            mac_address = self.address.mac().replace(":", "")
        except:
            mac_address = ''

        if is_broadcasting_ap != False:
            ssid = "gcwzero-"+mac_address

        else:
            try:
                with open(os.devnull, "w") as fnull:

                    output = SU.Popen(['/sbin/iw', 'dev', wlan, 'link'],
                                    stdout=SU.PIPE, stderr=fnull, close_fds=True).stdout.readlines()
                if output is not None:
                    for line in output:
                        if line.decode("utf-8").strip().startswith('SSID'):
                            ssid = line.decode("utf-8").split()[1]
            except:
                ssid = None
        return ssid

    def connect(self):
        """
        Associates the device with a given access point

        Args:
            ssid (str): The SSID with which to attempt a connection

        Returns:
            bool: True if connection was successful, False otherwise
        """
        return_status = False
        saved_file = self.configuration.netconfdir + parse.quote_plus(ssid) + ".conf"
        if os.path.exists(saved_file):
            shutil.copy2(saved_file, configuration.sysconfdir+"config-"+wlan+".conf")

        iface_status = self.interface.status()
        if iface_status != False:
            self.disconnect()
        else:
            try:
                self.interface.enable()
            except:
                self.interface.down()
                self.interface.disable()
                self.interface.enable()

        modal = Modal("Connecting...")
        modal.show()
        
        self.interface.up()

        connected_to_network = self.ssid()
        if connected_to_network != None:
            modal.clear()
            modal = Modal('Connected!', timeout=True)
            modal.show()
            return_status = True
        else:
            modal.clear()
            modal = Modal('Connection failed!', timeout=True)
            modal.show()
            return_status = False

        modal.clear()
        ui.redraw()
        return return_status

    def disconnect(self):
        """
        Disconnect from the currently associated access point
        """
        modal = Modal("Disconnecting...")
        modal.show()
        self.interface.down()
        modal.clear()
        ui.redraw()

    def scan(self):
        """
        Scans for access points in range

        Returns:
            List: A list of access points in range
        """
        interface_was_not_enabled = self.interface.enable()
        modal = Modal("Scanning...")
        modal.show()

        with open(os.devnull, "w") as fnull:
            output = SU.Popen(['sudo', '/usr/sbin/wlan-scan', wlan],
                            stdout=SU.PIPE, stderr=fnull,
                            close_fds=True, encoding="utf-8").stdout.readlines()

        aps = []

        for item in output:
            if len(item) > 2:
                try:
                    item = item.strip()
                    if item[-1] == ',':
                        item = item[0:-1]

                # FIXME: for now, we're going to ignore hidden networks.
                # In the future, we should probably display "<Hidden>" in the
                # list, and use the BSSID instead of the ESSID in the
                # configuration file.  I haven't looked into how to format that,
                # though.
                    if len(json.loads(item)['ssid'].strip()) != 0:
                        aps.append(json.loads(item))
                except:
                    pass
            else:
                pass

        # Sort by quality
        final = sorted(aps, key=lambda x: x['quality'], reverse=True)
        modal.clear()

        if interface_was_not_enabled:
            self.interface.down()
            self.interface.disable()

        return final

#TODO: I should probably use this code...
    # def scanForAPs():
        #     """Run when choosing the menu item "Scan for APs"; invokes the scan for nearby access points and builds a menu for wireless networks found in range.

        #     Returns:
        #         str: "ssid" if we were able to successfully scan for APs, otherwise "main"
        #     """
        #     global wirelessmenu
        #     global active_menu
        #     global access_points

        #     try:
        #         access_points = scanForNetworks()

        #     # No access points found
        #     except:
        #         active_menu = "main"

        #         access_points = {}
        #         text = ":("
        #         renderedtext = font_huge.render(
        #             text, True, colors["lightbg"],
        #             colors["darkbg"])
        #         textelement = renderedtext.get_rect()
        #         textelement.left = 192
        #         textelement.top = 96
        #         surface.blit(renderedtext, textelement)

        #     l = []
        #     if len(access_points) < 1:
        #         active_menu = "main"

        #         text = ":("
        #         renderedtext = font_huge.render(
        #             text, True, colors["lightbg"],
        #             colors["darkbg"])
        #         textelement = renderedtext.get_rect()
        #         textelement.left = 192
        #         textelement.top = 96
        #         surface.blit(renderedtext, textelement)
        #     else:
        #         for network in access_points:
        #             menuitem = [network['ssid'],
        #                         network['quality']]
        #             l.append(menuitem)
        #         createWirelessMenu()
        #         wirelessmenu.init(l, surface)
        #         wirelessmenu.draw()

        #         active_menu = "ssid"

        #     return active_menu

class AccessPoint():

    def status():
        """
        Determine status of hosting an access point

        Returns:
            bool: Return True if we are hosting an access point, otherwise return False
        """

        with open(os.devnull, "w") as fnull:
            output = SU.Popen(['sudo', '/sbin/ap', '--status'],
                            stderr=fnull, stdout=SU.PIPE, close_fds=True).stdout.readlines()
        for line in output:
            if line.decode("utf-8").strip() == 'ap is running':
                return True
            else:
                return False

    def start(self):
        """
        Create an access point for peer-to-peer connections

        Returns:
            bool: Returns True if the hosted AP was created successfully, or False otherwise
        """
        global wlan
        interface_status = self.interface.status()
        if interface_status != False:
            self.disconnect.network.disconnect()
        else:
            self.interface.enable()

        modal = Modal("Creating AP...")
        modal.show()

        if SU.Popen(['sudo', '/sbin/ap', '--start'], close_fds=True).wait() == 0:
            if self.status() == True:
                modal.clear()
                modal = Modal('AP created!', timeout=True)
                modal.show()
                ui.redraw()
                return True
            else:
                modal.clear()
                modal = Modal('Failed to create AP...', wait=True)
                modal.show()
                ui.redraw()
                return False
        else:
            modal.clear()
            modal = Modal('Failed to create AP...', wait=True)
            modal.show()
            ui.redraw()
            return False

    def stop(self):
        """
        Stop broadcasting the peer-to-peer access point

        Returns:
            bool: True if able to tear down the AP, False otherwise
        """
        try:
            if self.status():
                modal = Modal("Stopping AP...")
                modal.show()
                if SU.Popen(['sudo', '/sbin/ap', '--stop'],
                            close_fds=True).wait() == 0:

                    if self.status() == False:
                        modal.clear()
                        ui.redraw()
                        return True
                    else:
                        modal.clear()
                        modal = Modal('Failed to stop AP...', wait=True)
                        modal.show()
                        ui.redraw()
                        return False
                else:
                    modal.clear()
                    modal = Modal('Failed to stop AP...', wait=True)
                    modal.show()
                    ui.redraw()
                    return False
            else:
                return False
        except:
            return False

class UserInterface():
    def __init__(self):
        self.network = network.ssid()
        self.surface = self.display.surface
        self.draw.logo_bar()
        self.draw.status_bar()
        self.draw.access_point()
        self.draw.interface_status()

    class AccessPoint():
        """
        Draw information about the currently associated access point to the display
        """
        def __init__(self):
            self.mac_address = ''


        try:
            ssid = Network.ssid()
            try:
                key = Configuration.get_saved_key(ssid)
            except:
                mac_address = Address.mac().replace(":", "")
                key = "gcwzero-"+mac_address

            if ssid is not None:
                ssidlabel = "SSID"
                renderedssidlabel = Font.font_huge.render(
                    ssidlabel, True, colors["lightbg"], colors["darkbg"])
                ssidlabelelement = renderedssidlabel.get_rect()
                ssidlabelelement.right = 318
                ssidlabelelement.top = 36
                pygame.display.surface.blit(renderedssidlabel, ssidlabelelement)

                renderedssid = Font.font_mono_small.render(
                    ssid, True, colors["white"], colors["darkbg"])
                ssidelement = renderedssid.get_rect()
                ssidelement.right = 315
                ssidelement.top = 98
                pygame.display.surface.blit(renderedssid, ssidelement)

                enclabel = "Key"
                renderedenclabel = Font.font_huge.render(
                    enclabel, True, colors["lightbg"], colors["darkbg"])
                enclabelelement = renderedenclabel.get_rect()
                # Drawn a bit leftwards versus "SSID" text, so both right-align pixel-perfectly
                enclabelelement.right = 314
                enclabelelement.top = 116
                pygame.display.surface.blit(renderedenclabel, enclabelelement)

                renderedencp = Font.font_mono_small.render(
                    key, True, colors["white"], colors["darkbg"])
                encpelement = renderedencp.get_rect()
                encpelement.right = 315
                encpelement.top = 182
                pygame.display.surface.blit(renderedencp, encpelement)

        except:
            text = ":("
            renderedtext = Font.font_huge.render(
                text, True, colors["lightbg"], colors["darkbg"])
            textelement = renderedtext.get_rect()
            textelement.left = 192
            textelement.top = 98
            pygame.display.surface.blit(renderedtext, textelement)
            pygame.display.update()

    class logo_bar():
        """
        Draw the application name at the top of the screen as a PNG image
        """

        surface = pygame.image.load(
            (os.path.join(Configuration.datadir, 'gcwconnect.png'))).convert_alpha()

        pygame.draw.rect(
            pygame.display.surface, colors['lightbg'], (0, 0, screen_width, 34))
        pygame.draw.line(
            pygame.display.surface, colors['white'], (0, 34), (screen_width, 34))

        rect = pygame.display.surface.get_rect()
        rect.topleft = (8 + 5 + 1, 9)
        pygame.display.surface.blit(pygame.display.surface, rect)

    class status_bar():
        """
        Draw the status bar on the bottom of the screen
        """
        connected_to_network = Network.ssid()
        if connected_to_network is None:
            connected_to_network = "Not connected"
        global colors
        pygame.draw.rect(pygame.display.surface, colors['lightbg'],
                            (0, screen_height - 16, screen_width, 16))
        pygame.draw.line(
            pygame.display.surface, colors['white'], (0, screen_height - 17), (screen_width, screen_height - 17))
        wlantext = Font.font_mono_small.render(
            connected_to_network, True, colors['white'], colors['lightbg'])
        wlan_text = wlantext.get_rect()
        wlan_text.topleft = (2, screen_height - 16)
        pygame.display.surface.blit(wlantext, wlan_text)

    class interface_status():
        """
        Draw the status of the wlan interface on the status bar
        """
        global colors
        wlanstatus = Interface.status()
        if not wlanstatus:
            wlanstatus = wlan+" is off."
        else:
            wlanstatus = Network.ssid()

        wlantext = Font.font_mono_small.render(
            wlanstatus, True, colors['white'], colors['lightbg'])
        wlan_text = wlantext.get_rect()
        wlan_text.topleft = (2, screen_height - 15)
        pygame.display.surface.blit(wlantext, wlan_text)

        # Note that the leading space here is intentional, to more cleanly overdraw
        # any overly-long strings written to the screen beneath it (i.e. a very
        # long ESSID)
        if Interface.status():
            ip_address = Address.ip()
            if ip_address is None:
                ip_address = ''
            text = Font.font_mono_small.render(
                " "+ip_address, True, colors['white'], colors['lightbg'])
            interfacestatus_text = text.get_rect()
            interfacestatus_text.topright = (
                screen_width - 3, screen_height - 15)
            pygame.display.surface.blit(text, interfacestatus_text)
        else:
            mac = mac_addresses.get(wlan)
            if mac is not None:
                text = Font.font_mono_small.render(
                    " " + mac.decode("utf-8"),
                    True, colors['white'], colors['lightbg'])
                interfacestatus_text = text.get_rect()
                interfacestatus_text.topright = (
                    screen_width - 3, screen_height - 15)
                pygame.display.surface.blit(text, interfacestatus_text)

    class Menu():
        def main(self):
            return menu.Main(network=self.network, ap=self.ap, menu="main")

        def ssid():
            return menu.Networks()

# TODO: This probably doesn't work
    def draw(self, menu):
        pygame.display.surface.blit(self, menu)

    def redraw(self):
        """
        Clear the display completely, and redraws it with all of the elements which are appropriate for the current context.
        """

        self.surface.fill(colors['darkbg'])
        self.draw.logo_bar()
        self.draw.menu.main()
        if wirelessmenu is not None:
            wirelessmenu.draw()
            pygame.draw.rect(
                self.surface, colors['darkbg'], (0, 208, screen_width, 16))
            Hint("select", "Edit", 4, screen_height - 30)
            Hint("a", "Connect", 75, screen_height - 30)
            Hint("b", "/", 130, screen_height - 30)
            Hint("left", "Back", 145, screen_height - 30)
        if active_menu == "main":
            pygame.draw.rect(self.surface, colors['darkbg'], (0, 208, screen_width, 16))
            Hint("a", "Select", 8, screen_height - 30)
        if active_menu == "saved":
            Hint("y", "Forget", 195, screen_height - 30)
        if active_menu == "ssid":
            Hint("y", "Rescan", 195, screen_height - 30)

        self.draw.status_bar()
        self.draw.interface_status()
        self.display.update()

class Menu():

    def __init__(self):
        self.menu = ""
        self.surface = self.display.surface
        self.font = Font().font_medium
        self.dest_surface = self.surface
        self.canvas_color = colors["darkbg"]

        self.elements = []

    class Networks():
        """Draw a list of access points in a given Menu
        """
        def __init__(self):
            self.set_elements([])
            self.selected_item = 0
            self.origin = (0, 0)
            self.menu_width = 0
            self.menu_height = 0
            self.selection_color = colors["activeselbg"]
            self.text_color = colors["activetext"]

        def set_elements(self, elements):
            """Define the access points to be displayed in the menu.

            Args:
                elements (list): The list of elements to be displayed.
            """
            self.elements = elements

        def get_item_width(self, element):
            """Determine the width of a given element

            Args:
                element: The element to get the width of.

            Returns:
                int: The element's width plus the corresponding spacing.
            """
            the_ssid = element[0]
            render = self.font.render(the_ssid, 1, self.text_color)
            spacing = 15
            return render.get_rect().width + spacing * 2

        def get_item_height(self, element):
            """Determine the height of a given element

            Args:
                element: The element to get the height of.

            Returns:
                int: The element's height plus the corresponding spacing.
            """
            render = self.font.render(element[0], 1, self.text_color)
            spacing = 6
            return (render.get_rect().height + spacing * 2) + 5

        def render_element(self, menu_surface, element, left, top):
            """Render an element into the menu.

            Args:
                menu_surface (pygame.surface): The pygame surface to render the element into.
                element (): The element to render.
                left (int): The left position of the element.
                top (int): The top position of the element.
            """
            the_ssid = element[0]
            # Wifi signal icons
            percent = element[1]

            try:
                if percent >= 6 and percent <= 24:
                    signal_icon = 'wifi-0.png'
                elif percent >= 25 and percent <= 49:
                    signal_icon = 'wifi-1.png'
                elif percent >= 50 and percent <= 74:
                    signal_icon = 'wifi-2.png'
                elif percent >= 75:
                    signal_icon = 'wifi-3.png'
                else:
                    signal_icon = 'transparent.png'
            except:
                signal_icon = 'transparent.png'
                percent = None

            qual_img = pygame.image.load(
                (os.path.join(self.configuration.datadir, signal_icon))).convert_alpha()
            # enc_img = pygame.image.load((os.path.join(datadir, enc_icon))).convert_alpha()

            ssid = self.font.font_mono_small.render(the_ssid, 1, self.text_color)
            if type(percent) == int:
                self.strength = self.font.font_small.render(
                    str(str(percent) + "%").rjust(4), 1, colors["lightgrey"])
            spacing = 2

            menu_surface.blit(ssid, (int(round(left + spacing)), int(round(top))))
            # menu_surface.blit(enc, (int(round(left + enc_img.get_rect().width + 12)), int(round(top + 18))))
            # menu_surface.blit(enc_img, (int(round(left + 8)), int(round((top + 24) -
            # (enc_img.get_rect().height / 2)))))
            if type(percent) == int:
                menu_surface.blit(self.strength, (left + 137, top + 18,
                                            self.strength.get_rect().width, self.strength.get_rect().height))
            qual_x = left + 200 - qual_img.get_rect().width - 3
            qual_y = top + 7 + 6
            qual_y = top + 7 + 6
            qual_y = top + 7 + 6
            menu_surface.blit(qual_img, (qual_x, qual_y))
            pygame.display.update()

        def draw(self, move=0):
            """Draw the menu on the display.

            Args:
                move (int, optional): The element ID of the menu item being moved to in the list. Defaults to 0.

            Returns:
                int: The selected item ID.
            """
            if len(self.elements) == 0:
                return

            if move != 0:
                self.selected_item += move
                if self.selected_item < 0:
                    self.selected_item = 0
                elif self.selected_item >= len(self.elements):
                    self.selected_item = len(self.elements) - 1

            # Which items are to be shown?
            if self.selected_item <= 2:  # We're at the top
                visible_elements = self.elements[0:5]
                selected_within_visible = self.selected_item
            # We're at the bottom
            elif self.selected_item >= len(self.elements) - 3:
                visible_elements = self.elements[-5:]
                selected_within_visible = self.selected_item - \
                    (len(self.elements) - len(visible_elements))
            else:  # The list is larger than 5 elements, and we're in the middle
                visible_elements = self.elements[self.selected_item -
                                                2:self.selected_item + 3]
                selected_within_visible = 2

            max_width = 320 - self.origin[0] - 3

            # And now the height
            heights = [self.get_item_height(visible_element)
                    for visible_element in visible_elements]
            total_height = sum(heights)

            # Background
            menu_surface = pygame.Surface((max_width, total_height))
            menu_surface.fill(self.canvas_color)

            # Selection
            left = 0
            top = sum(heights[0:selected_within_visible])
            width = max_width
            height = heights[selected_within_visible]
            selection_rect = (left, top, width, height)
            pygame.draw.rect(menu_surface, self.selection_color, selection_rect)

            # Elements
            top = 0
            for i in range(len(visible_elements)):
                self.render_element(menu_surface, visible_elements[i], 0, top)
                top += heights[i]
            self.dest_surface.blit(menu_surface, self.origin)
            return self.selected_item
    class Main():
        def __init__(self):
            self.set_elements([])
            self.selected_item = 0
            self.origin = (0, 0)
            self.menu_width = 0
            self.menu_height = 0
            self.selection_color = colors["activeselbg"]
            self.text_color = colors["activetext"]
            self.draw()

        def move_menu(self, top, left):
            """Move the menu to a given position on the display, e.g. for a submenu

            Args:
                top (int): The position of the top of the menu.
                left (int): The position of the left of the menu.
            """
            self.origin = (top, left)

        def set_colors(self, text, selection, background):
            """Define the colors to draw the menu with.

            Args:
                text (0-255, 0-255, 0-255): The color to use for the menu item text.
                selection (0-255, 0-255, 0-255): The color to use for the selected menu item background.
                background (0-255, 0-255, 0-255): The color to use for the unselected menu items.
            """
            self.text_color = text
            self.selection_color = selection

        def set_elements(self, elements):
            """Define the menu items to be displayed.

            Args:
                elements (list): The list of elements to be displayed.
            """
            self.elements = elements

        def get_position(self):
            """Get the position of the currently selected menu item in the list.

            Returns:
                int: The position of the currently selected menu item in the list, starting from 0.
            """
            return self.selected_item

        def get_selected(self):
            """Get the selected menu item

            Returns:
                str: The text of the currently selected menu item.
            """
            return self.elements[self.selected_item]

        def init(self, elements, dest_surface):
            """Initialize a new menu

            Args:
                elements (list): The list of menu items to initialize the menu with.
                dest_surface (pygame.surface): The pygame surface to draw the menu on.
            """

            self.set_elements(elements)
            self.dest_surface = dest_surface

        def draw(self, move=0):
            """Draw the menu on the display.

            Args:
                move (int, optional): The element ID of the menu item being moved to in the list. Defaults to 0.

            Returns:
                int: The selected item ID.
            """
            # Clear any old text (like from apinfo()), but don't overwrite button hint area above statusbar
            pygame.draw.rect(self.surface, colors['darkbg'], (0, 35, 320, 173))
            self.elements = self.define_elements()

            if len(self.elements) == 0:
                return None

            self.selected_item = (self.selected_item + move) % len(self.elements)

            # Which items are to be shown?
            if self.selected_item <= 2:  # We're at the top
                visible_elements = self.elements[0:6]
                selected_within_visible = self.selected_item
            # We're at the bottom
            elif self.selected_item >= len(self.elements) - 3:
                visible_elements = self.elements[-6:]
                selected_within_visible = self.selected_item - \
                    (len(self.elements) - len(visible_elements))
            else:  # The list is larger than 5 elements, and we're in the middle
                visible_elements = self.elements[self.selected_item -
                                                2:self.selected_item + 3]
                selected_within_visible = 2

            # What width does everything have?
            max_width = max([self.get_item_width(visible_element)
                            for visible_element in visible_elements])
            # And now the height
            heights = [self.get_item_height(visible_element)
                    for visible_element in visible_elements]
            total_height = sum(heights)

            # Background
            menu_surface = pygame.Surface((max_width, total_height))
            menu_surface.fill(self.canvas_color)

            # Selection
            left = 0
            top = sum(heights[0:selected_within_visible])
            width = max_width
            height = heights[selected_within_visible]
            selection_rect = (left, top, width, height)
            pygame.draw.rect(menu_surface, self.selection_color, selection_rect)

            # Clear any error elements
            error_rect = (left+width+8, 35, 192, 172)
            pygame.draw.rect(self.surface, colors['darkbg'], error_rect)

            # Elements
            top = 0
            for i in range(len(visible_elements)):
                self.render_element(menu_surface, visible_elements[i], 0, top)
                top += heights[i]
            self.dest_surface.blit(menu_surface, self.origin)
            return self.selected_item

        def get_item_height(self, element):
            """Determine the height of a given element

            Args:
                element: The element to get the height of.

            Returns:
                int: The element's height plus the corresponding spacing.
            """
            render = self.font.render(element, 1, self.text_color)
            spacing = 5
            return render.get_rect().height + spacing * 2

        def get_item_width(self, element):
            """Determine the width of a given element

            Args:
                element: The element to get the width of.

            Returns:
                int: The element's width plus the corresponding spacing.
            """
            render = self.font.render(element, 1, self.text_color)
            spacing = 5
            return render.get_rect().width + spacing * 2

        def render_element(self, menu_surface, element, left, top):
            """Render an element into the menu.

            Args:
                menu_surface (pygame.surface): The pygame surface to render the element into.
                element (): The element to render.
                left (int): The left position of the element.
                top (int): The top position of the element.
            """
            render = self.font.render(element, 1, self.text_color)
            spacing = 5
            menu_surface.blit(render, (int(round(left + spacing)), int(
                round(top + spacing)), render.get_rect().width, render.get_rect().height))

        def define_elements(self):
            """Define items which appear in the main menu
            """

            elems = ['Quit']

            ap = self.network.ssid()
            is_hosting_ap = self.ap.status()

            if ap is not None:
                elems = ['AP info'] + elems
            else:
                elems = ['Create AP'] + elems

            elems = ["Saved Networks", "Scan for APs", "Manual Setup"] + elems

            interface_status = self.interface.status()
            if interface_status == "Connected" or is_hosting_ap:
                elems = ['Disconnect'] + elems

            return elems

# TODO: This is known to be broken.
    class Saved():
        """Create a menu of all saved networks on disk
        """
        saved_networks = Configuration.get_saved_networks()

        if len(saved_networks) > 0:
            l = []
            for item in sorted(iter(saved_networks.keys()),
                                key=lambda x: saved_networks[x]['ESSID']):
                detail = saved_networks[item]
                l.append([detail['ESSID'], detail['Key']])
            # createWirelessMenu()
            # wirelessmenu.init(l, surface)
            # wirelessmenu.draw()
        else:
            text = 'empty'
            renderedtext = Font.font_huge.render(
                text, True, colors["lightbg"], colors["darkbg"])
            textelement = renderedtext.get_rect()
            textelement.left = 152
            textelement.top = 96
            # surface.blit(renderedtext, textelement)
            # ui.redraw()

    def switch(self, to=""):
        """Chooses which currently displayed menu or submenu to use for navigation.
        """

        if to == "main":
            menu.set_colors(colors['activetext'],
                            colors['activeselbg'], colors['darkbg'])
            if wirelessmenu is not None:
                wirelessmenu.set_colors(
                    colors['inactivetext'], colors['inactiveselbg'], colors['darkbg'])
        elif to == "ssid" or to == "saved":
            menu.set_colors(colors['inactivetext'],
                            colors['inactiveselbg'], colors['darkbg'])
            wirelessmenu.set_colors(
                colors['activetext'], colors['activeselbg'], colors['darkbg'])
        self.menu = to
        self.display.redraw()
        return self.menu

    def get_active(self):
        return self.menu

class Modal(text = "", wait=False, timeout=False, query=False):
    """
    Draw a Modal window in the middle of the screen

    Args:
        text (str): The Modal window text to be displayed.
        wait (bool, optional): Whether to wait for a button press to dismiss the Modal window. Defaults to False.
        timeout (bool, optional): Whether to automatically close the Modal window after 2.5 seconds. Defaults to False.
        query (bool, optional): Whether to wait for a button press to confirm or cancel. Defaults to False.

    Returns:
        bool: Returns True once the Modal window has been closed.
    """
    def __init__(self):
        self.surface = self.display.surface
        self.font = Font()
    def show(self):
        self.draw()

    def draw(self):
        self.display.draw_scrim()

        # Left, top, width, height
        dialog = pygame.draw.rect(self.surface, colors['lightbg'], (round((
            screen_width - 192)/2), round((screen_height - 72)/2), 192, 72))
        pygame.draw.rect(self.surface, colors['white'], (round((
            screen_width - 194)/2 - 2), round((screen_height - 74)/2 - 2), 194, 74), 2)

        text = self.font.font_medium.render(self.text, True, colors['white'], colors['lightbg'])
        modal_text = text.get_rect()
        modal_text.center = dialog.center

        self.surface.blit(text, modal_text)
        self.display.update()

        if self.wait:
            Hint("a", "Continue", round((screen_width - 192) /
                                                2 + 66 + 74), round((screen_height - 72)/2 - 15+70), colors['lightbg'])
            self.display.update()
        elif self.timeout:
            time.sleep(2.5)
            ui.redraw()
        elif self.query:
            Hint("a", "Confirm", round((screen_width - 192)/2 + 66 + 74
                                                ), round((screen_height - 72)/2 - 15 + 70), colors['lightbg'])
            Hint("b", "Cancel", round((screen_width - 192)/2 + 11 + 74
                                                ), round((screen_height - 72)/2 - 15 + 70), colors['lightbg'])
            self.display.update()
            while True:
                for event in pygame.event.get():
                    if event.type == KEYDOWN:
                        if event.key == K_LCTRL:
                            self.clear()
                            pygame.display.update()
                            return True
                        elif event.key == K_LALT:
                            self.clear()
                            pygame.display.update()
                            return True

        if not self.wait:
            self.clear()
            pygame.display.update()
            return True

        while True:
            for event in pygame.event.get():
                if event.type == KEYDOWN and event.key == K_LCTRL:
                    self.clear()
                    ui.redraw()
                    return True

    def clear(self):
        self.remove()
        self.display.remove_scrim()

class Hint():
    """
    Draw colorful button icons and labels
    """

    def __init__(self, button, text, x, y, bg=colors["darkbg"]):
        self.button = button
        self.text = text
        self.x = x
        self.y = y
        self.bg = bg

        self.font = Font()
        self.draw()

    def draw(self):
        if self.button == 'l' or self.button == 'r':
            if self.button == 'l':
                AaFilledCircle(colors["black"], (self.x, self.y+5), 5)
                pygame.draw.rect(
                    self.surface, colors["black"], (self.x-5, self.y+6, 10, 5))
                button = pygame.draw.rect(
                    self.surface, colors["black"], (self.x, self.y, 15, 11))

            if self.button == 'r':
                AaFilledCircle(
                    colors["black"], (self.x+8, self.y+5), 5)
                pygame.draw.rect(
                    self.surface, colors["black"], (self.x+4, self.y+6, 10, 5))
                button = pygame.draw.rect(
                    self.surface, colors["black"], (self.x-5, self.y, 15, 11))

            labeltext = self.font.font_tiny.render(
                self.button.upper(), True, colors["white"], colors["black"])
            buttontext = labeltext.get_rect()
            buttontext.center = self.button.center
            self.surface.blit(labeltext, buttontext)

            button = pygame.draw.rect(
                self.surface, colors["lightbg"], (self.x+26, self.y+5, 1, 1))
            text = self.font.font_tiny.render(
                self.text, True, colors["white"], colors["lightbg"])
            buttontext = text.get_rect()
            buttontext.center = button.center
            self.surface.blit(text, buttontext)

        if self.button == "select" or self.button == "start":
            lbox = AaFilledCircle(
                colors["black"], (self.x+5, self.y+5), 6)
            rbox = AaFilledCircle(
                colors["black"], (self.x+29, self.y+5), 6)
            straightbox = lbox.union(rbox)
            buttoncenter = straightbox.center
            if self.button == 'select':
                straightbox.y = lbox.center[1]
            straightbox.height = int(round((straightbox.height + 1) / 2))
            pygame.draw.rect(self.surface, colors["black"], straightbox)

            roundedbox = Rect(
                lbox.midtop, (rbox.midtop[0] - lbox.midtop[0], lbox.height - straightbox.height))
            if self.button == 'start':
                roundedbox.bottomleft = lbox.midbottom
            pygame.draw.rect(self.surface, colors["black"], roundedbox)
            text = self.font.font_tiny.render(
                self.button.upper(), True, colors["white"], colors["black"])
            buttontext = text.get_rect()
            buttontext.center = buttoncenter
            buttontext.move_ip(0, 1)
            self.surface.blit(text, buttontext)

            labelblock = pygame.draw.rect(
                self.surface, self.bg, (self.x+40, self.y, 25, 14))
            labeltext = self.font.font_tiny.render(
                self.text, True, colors["white"], self.bg)
            self.surface.blit(labeltext, labelblock)

        elif self.button in ('a', 'b', 'x', 'y'):
            if self.button == "a":
                self.color = colors["green"]
            elif self.button == "b":
                self.color = colors["blue"]
            elif self.button == "x":
                self.color = colors["red"]
            elif self.button == "y":
                self.color = colors["yellow"]

            labelblock = pygame.draw.rect(
                self.surface, self.bg, (self.x+10, self.y, 35, 14))
            labeltext = self.font.font_tiny.render(
                self.text, True, colors["white"], self.bg)
            self.surface.blit(labeltext, labelblock)

            button = AaFilledCircle(
                self.color, (self.x, self.y+5), 6)  # (x, y)
            text = self.font.font_tiny.render(
                self.button.upper(), True, colors["white"], self.color)
            buttontext = text.get_rect()
            buttontext.center = button.center
            self.surface.blit(text, buttontext)

        elif self.button in ('left', 'right', 'up', 'down'):

            # Vertical
            pygame.draw.rect(
                self.surface, colors["black"], (self.x+5, self.y-1, 4, 12))
            pygame.draw.rect(
                self.surface, colors["black"], (self.x+6, self.y-2, 2, 14))

            # Horizontal
            pygame.draw.rect(
                self.surface, colors["black"], (self.x+1, self.y+3, 12, 4))
            pygame.draw.rect(
                self.surface, colors["black"], (self.x, self.y+4, 14, 2))

            if self.button == "left":
                pygame.draw.rect(
                    self.surface, colors["white"], (self.x+2, self.y+4, 3, 2))
            elif self.button == "right":
                pygame.draw.rect(
                    self.surface, colors["white"], (self.x+9, self.y+4, 3, 2))
            elif self.button == "up":
                pygame.draw.rect(
                    self.surface, colors["white"], (self.x+6, self.y+1, 2, 3))
            elif self.button == "down":
                pygame.draw.rect(
                    self.surface, colors["white"], (self.x+6, self.y+7, 2, 3))

            labelblock = pygame.draw.rect(
                self.surface, self.bg, (self.x+20, self.y, 35, 14))
            labeltext = self.font.font_tiny.render(
                self.text, True, (255, 255, 255), self.bg)
            self.surface.blit(labeltext, labelblock)

class AaFilledCircle(center = None, radius = None):
    """
    Helper function to draw anti-aliased circles using an interface similar
    to pygame.draw.circle.

    Args:
        color (0-255, 0-255, 0-255): The color used to draw the circle.
        center (int,int): The coordinates of the center of the circle.
        radius (int): The distance to the center of the circle to the edge.

    Returns:
        [type]: [description]
    """
    def __init__(self):
        self.surface = self.display.surface
        x, y = self.center
        pygame.gfxdraw.aacircle(self.surface, x, y, self.radius, self.color)
        pygame.gfxdraw.filled_circle(self.surface, x, y, self.radius, self.color)
        return Rect(x - self.radius, y - self.radius, self.radius * 2 + 1, self.radius * 2 + 1)

class Radio():
    """
    Draw a standard radio button
    """

    def __init__(self):
        self.surface = self.display.surface
        self.font = Font()
        self.key = []
        self.selection_color = colors['activeselbg']
        self.text_color = colors['activetext']
        self.selection_position = (0, 0)
        self.selected_item = 0

    def init(self, key, row, column):
        self.key = key
        self.row = row
        self.column = column
        self.draw_key()

    def draw_key(self):
        self.key_width = 64
        self.key_height = 16

        top = 136 + self.row * 20
        left = 32 + self.column * 64

        if len(self.key) > 1:
            self.key_width = 64
        radiobutton = AaFilledCircle(colors['white'], (left, top), 8)
        AaFilledCircle(colors['darkbg'], (left, top), 6)
        text = self.font.font_medium.render(
            self.key, True, (255, 255, 255), colors['darkbg'])
        label = text.get_rect()
        label.left = radiobutton.right + 8
        label.top = radiobutton.top + 4
        self.surface.blit(text, label)

class Keyboard(board = None, direction = None):
    def __init__(self):
        if self.board is None:
            self.board = 'qwertyNormal'

        # Define key layouts for the soft keyboard
        self.layouts = {
            'qwertyNormal': (
                ('`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='),
                ('q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\'),
                ('a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\''),
                ('z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/'),
            ),
            'qwertyShift': (
                ('~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+'),
                ('Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '|'),
                ('A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"'),
                ('Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?'),
            )

            # TODO: We might want an international keyboard for our overseas friends.
            # If you find this message because you're unable to enter your key, please
            # open an issue on GitHub
        }

        # Define which order the keyboards are cycled in
        self.cycle_order = ('qwertyNormal', 'qwertyShift')

    class Label(size=24, kind="ssid"):
        """
        Display text entered using the soft keyboard on the display.

        Args:
            kind (str): The kind of input we're asking for; generally "ssid" or "key".
            size (int, optional): Font size of the text to display. Defaults to 24.
        """

        def __init__(self):
            self.size = 24

            if self.kind == "ssid":
                pygame.draw.rect(
                    self.surface, colors['darkbg'], (0, 100, 320, 34))
                labelblock = pygame.draw.rect(
                    self.surface, colors['white'], (0, 35, 320, 20))
                labeltext = self.font.font_large.render(
                    "Enter new SSID", True, colors['lightbg'], colors['white'])
                label = labeltext.get_rect()
                label.center = labelblock.center
                self.surface.blit(labeltext, label)

            elif self.kind == "key":
                labelblock = pygame.draw.rect(
                    self.surface, colors['white'], (0, 35, 320, 20))
                labeltext = self.font.font_large.render(
                    "Enter network key", True, colors['lightbg'], colors['white'])
                label = labeltext.get_rect()
                label.center = labelblock.center
                self.surface.blit(labeltext, label)

            self.hintblock = pygame.draw.rect(
                self.surface, colors['darkbg'], (0, 100, 320, 34))

            # Input area
            bg = pygame.draw.rect(
                self.surface, colors['white'], (0, 55, 320, 45))
            text = "[ "
            text += passphrase
            text += " ]"
            pw = self.font.font_mono_small.render(
                text, True, (0, 0, 0), colors['white'])
            pwtext = pw.get_rect()
            pwtext.center = bg.center
            self.surface.blit(pw, pwtext)
            pygame.display.update()

    class Key:
        """
        Draw a single key on the keyboard
        """

        def __init__(self):
            self.input = None
            self.key = []
            self.selection_color = colors['activeselbg']
            self.text_color = colors['activetext']
            self.selection_position = (0, 0)
            self.selected_item = 0

        def init(self, key, row, column):
            self.key = key
            self.row = row
            self.column = column
            self.draw_key()

        def draw_key(self):
            key_width = 16
            key_height = 16

            top = 136 + self.row * 20
            left = 32 + self.column * 20

            if len(self.key) > 1:
                key_width = 36
            keybox = pygame.draw.rect(
                self.surface, colors['lightbg'], (left, top, key_width, key_height))
            text = self.font.font_medium.render(
                self.key, True, colors['white'], colors['lightbg'])
            label = text.get_rect()
            label.center = keybox.center
            label.y -= 1
            self.surface.blit(text, label)

        def get_selected(self):
            return self.selected_item

        def highlight(self, pos='[0,0]'):
            def __init__(self):
                self.pos = pos
            left_margin = 32 #TODO: Make these values dynamic, to fit the keyboard on any display
            top_margin = 136 #TODO: Make these values dynamic, to fit the keyboard on any display

            if self.pos[0] > left_margin:
                x = left_margin + (16 * (self.pos[0]))
            else:
                x = left_margin + (16 * self.pos[0]) + (self.pos[0] * 4)

            if self.pos[1] > top_margin:
                y = top_margin + (16 * (self.pos[1]))
            else:
                y = top_margin + (16 * self.pos[1]) + (self.pos[1] * 4)

            pointlist = [
                (x, y),
                (x + 16, y),
                (x + 16, y + 16),
                (x, y + 16),
                (x, y)
            ]

            self.lines = pygame.draw.lines(
                self.surface, (255, 255, 255), True, pointlist, 1)
            pygame.display.update()

    def next(self):
        """
        Cycle the keyboard keys through keyLayouts using keyboardCycleOrder

        Args:
            board (str): The currently displayed keyboard layout.

        Returns:
            str: The next keyboard to be displayed.
        """
        return self.cycle_order[
            (self.cycle_order.index(self.board) + 1) % len(self.cycle_order)
        ]

    def draw(self):
        """Draw the keyboard to the display

        Args:
            board (str): The name of the keyboard to draw, as defined in keyLayouts
        """


        # Draw keyboard background
        pygame.draw.rect(self.surface, colors['darkbg'], (0, 134, 320, 106))

        # Draw bottom background
        pygame.draw.rect(self.surface, colors['lightbg'], (0, 224, 320, 16))
        pygame.draw.line(self.surface, colors['white'],      (0, 223), (320, 223))

        #    Button		Label		x-pos	y-pos	Background color
        Hint("select", 	"Cancel", 	4, 		227, 	colors['lightbg'])
        Hint("start", 	"Finish", 	75, 	227, 	colors['lightbg'])
        Hint("x", 		"Delete",	155, 	227, 	colors['lightbg'])
        Hint("y", 		"Shift", 	200, 	227, 	colors['lightbg'])
        Hint("b", 		"Space", 	240, 	227, 	colors['lightbg'])
        Hint("a", 		"Enter", 	285, 	227, 	colors['lightbg'])

        # Draw the keys
        z = self.Key()
        for row, rowData in enumerate(self.layouts[self.board]):
            for column, label in enumerate(rowData):
                z.init(label, row, column)


        pygame.display.update()

    def get_user_input(self):
        """Gets some input from the user via a software keyboard.

        Args:
            keyboard (str): The keyboard layout to display.
            kind (str): The kind of input we're asking for; generally, "ssid" or "key".
            ssid (str, optional): The SSID to pre-populate the input area with, useful for editing an exisiting SSID. Defaults to "".

        Returns:
            str: The text which was entered via the software keyboard.
        """

        if not self.selected_key:
            self.selected_key = [0, 0]

        def clampRow():
            self.selected_key[1] = min(self.selected_key[1], len(layout) - 1)

        def clampColumn():
            self.selected_key[0] = min(self.selected_key[0], len(
                layout[self.selected_key[1]]) - 1)

        layout = self.layouts[self.board]

        if self.direction == "swap":
            # Clamp row first since each row can have a different number of columns.
            clampRow()
            clampColumn()
        elif self.direction == "up":
            self.selected_key[1] = (self.selected_key[1] - 1) % len(layout)
            clampColumn()
        elif self.direction == "down":
            self.selected_key[1] = (self.selected_key[1] + 1) % len(layout)
            clampColumn()
        elif self.direction == "left":
            self.selected_key[0] = (self.selected_key[0] - \
                                1) % len(layout[self.selected_key[1]])
        elif self.direction == "right":
            self.selected_key[0] = (self.selected_key[0] + \
                                1) % len(layout[self.selected_key[1]])
        elif self.direction == "select":
            self.input += layout[self.selected_key[1]][self.selected_key[0]]
            if len(self.input) > 20:
                self.interface.draw.logo_bar()
                self.draw.Label(self, kind=self.kind, size=12)
            else:
                self.draw.Label(self, kind=self.kind)
        elif self.direction == "space":
            self.input += ' '
            if len(self.input) > 20:
                self.interface.draw.logo_bar()
                self.draw.Label(self, kind=self.kind, size=12)
            else:
                self.draw.Label(self, kind=self.kind)
        elif self.direction == "delete":
            if len(self.input) > 0:
                self.input = self.input[:-1]
                self.interface.draw.logo_bar()
                if len(self.input) > 20:
                    self.draw.Label(self, kind=self.kind, size=12)
                else:
                    self.draw.Label(self, kind=self.kind)

        self.key.highlight(self, self.selected_key)

        return self.input


###############################################################################
#                                                                             #
#                               Main Application                              #
#                                                                             #
###############################################################################

display = Display()
configuration = Configuration()
address = Address()
ap = AccessPoint()
interface = Interface()
network = Network()

menu = Menu()
main_menu = menu.Main()
main_menu.move_menu(3, 41)

wirelessmenu = menu.Wireless()
wirelessmenu.move_menu(116, 40)

ui = UserInterface()
keyboard = Keyboard()

if __name__ == "__main__":
    # Persistent variables
    access_points = {}

    while True:
        time.sleep(0.01)
        for event in pygame.event.get():
            # GCW-Zero keycodes:
            # A = K_LCTRL
            # B = K_LALT
            # X = K_LSHIFT
            # Y = K_SPACE
            # L = K_TAB
            # R = K_BACKSPACE
            # start = K_RETURN
            # select = K_ESCAPE
            # power up = K_KP0
            # power down = K_PAUSE

            if event.type == QUIT:
                pygame.display.quit()
                sys.exit()

            elif event.type == KEYDOWN:
                if event.key == K_PAUSE: 		# Power down
                    pass
                elif event.key == K_TAB: 		# Left shoulder button
                    pass
                elif event.key == K_BACKSPACE: 	# Right shoulder button
                    pass
                elif event.key == K_KP0:		# Power up
                    pass
                elif event.key == K_UP: 		# Arrow up the menu
                    if menu.get_active() == "main":
                        main_menu.draw(-1)
                    elif menu.get_active() == "ssid" or menu.get_active() == "saved":
                        wirelessmenu.draw(-1)
                elif event.key == K_DOWN: 		# Arrow down the menu
                    if menu.get_active() == "main":
                        main_menu.draw(1)
                    elif menu.get_active() == "ssid" or menu.get_active() == "saved":
                        wirelessmenu.draw(1)
                elif event.key == K_RIGHT:
                    if wirelessmenu is not None and menu.get_active() == "main":
                        menu.switch("ssid")
                        ui.redraw()
                elif event.key == K_LALT or event.key == K_LEFT:
                    if menu.get_active() == "ssid" or menu.get_active() == "saved":
                        wirelessmenu.remove()
                        menu.switch("main")
                        ui.redraw()
                    elif event.key == K_LALT:
                        pygame.display.quit()
                        sys.exit()

                # Y key pressed
                elif event.key == K_SPACE:
                    if menu.get_active() == "saved":
                        confirm = Modal("Forget AP configuration?", query=True)
                        if confirm:
                            os.remove(
                                configuration.netconfdir+parse.quote_plus(str(
                                    wirelessmenu.get_selected()[0]))+".conf")
                        wirelessmenu = menu.Saved()
                        wirelessmenu.show()
                        ui.redraw()
                        try:
                            if len(access_points) < 1:
                                wirelessmenu.remove()
                        except NameError:
                            wirelessmenu.remove()

                        menu.switch("main")

                    elif menu.get_active() == "ssid":
                        active_menu = ap.scan()
                        if menu.get_active() != "ssid":
                            menu.switch(menu.get_active())
                        else:
                            ui.redraw()

                # A key pressed
                elif event.key == K_LCTRL or event.key == K_RETURN:
                    # Main menu
                    if menu.get_active() == "main":
                        if menu.get_selected() == 'Disconnect':
                            ap.disconnect()
                            ui.redraw()
                        elif menu.get_selected() == 'Scan for APs':
                            menu.switch("ssid")
                        elif menu.get_selected() == 'Manual Setup':
                            ssid = ''
                            passphrase = ''
                            selected_key = ''
                            securitykey = ''

                            # Get SSID from the user
                            ssid = network.ssid()
                            if not ssid == '':
                                # Get key from the user
                                passphrase = keyboard.get_user_input("key")
                                ui.redraw()
                                configuration.write(ssid, passphrase)
                                ap.connect(ssid)

                        elif menu.get_selected() == 'Saved Networks':
                            wirelessmenu = menu.Saved()
                            wirelessmenu.draw()
                            try:
                                menu.switch("saved")
                            except:
                                menu.switch("main")
                            ui.redraw()
                        elif menu.get_selected() == 'Create AP':
                            ap.start()

                        elif menu.get_selected() == 'AP info':
                            ap.info()

                        elif menu.get_selected() == 'Quit':
                            pygame.display.quit()
                            try:
                                sys.exit()
                            except:
                                exit(0)

                    # SSID menu
                    elif menu.get_active() == "ssid":
                        ssid = ""
                        access_points = network.scan()
                        for network in access_points:
                            if network['ssid'].split("-")[0] == "gcwzero":
                                ssid = network['ssid']
                                conf = configuration.netconfdir + \
                                    parse.quote_plus(ssid) + ".conf"
                                passphrase = ssid.split("-")[1]
                                ap.connect(ssid)
                            else:
                                position = int(wirelessmenu.get_position())
                                ssid = access_points[position]['ssid']
                                conf = configuration.netconfdir + \
                                    parse.quote_plus(ssid) + ".conf"
                                if not os.path.exists(conf):
                                    passphrase = ''
                                    selected_key = ''
                                    securitykey = ''
                                    menu.Label("key")
                                    passphrase = keyboard.get_user_input(
                                        "qwertyNormal", "key", ssid)
                                else:
                                    ap.connect(ssid)
                            break

                    # Saved Networks menu
                    elif active_menu == "saved":
                        saved_networks = configuration.get_saved_networks()
                        for network in saved_networks:
                            position = int(wirelessmenu.get_position())
                            ssid = saved_networks[position]['ESSID']
                            shutil.copy2(configuration.netconfdir + parse.quote_plus(ssid) +
                                            ".conf", configuration.sysconfdir+"config-"+wlan+".conf")
                            passphrase = saved_networks[position]['Key']
                            ap.connect(ssid)
                            break

                elif event.key == K_ESCAPE:
                    # Allow us to edit the existing key
                    if menu.get_active() == "ssid":
                        ssid = ""
                        access_points = ap.scan()
                        for network in access_points:
                            position = int(wirelessmenu.get_position())
                            ssid = access_points[position]['ESSID']
                            passphrase = ''
                            selected_key = ''
                            securitykey = ''
                            keyboard.Label("key")
                            securitykey = keyboard.get_user_input("qwertyNormal", "key", ssid)
                            configuration.write(ssid, securitykey)

                    # Allow us to edit the existing key
                    if menu.get_active() == "saved":
                        saved_networks = configuration.get_saved_networks()
                        position = int(wirelessmenu.get_position())
                        ssid = saved_networks[position]['ESSID']
                        passphrase = saved_networks[position]['Key']
                        selected_key = ''
                        securitykey = ''
                        menu.Label("key")
                        securitykey = menu.get_user_input("qwertyNormal", "key", ssid)
                        configuration.write(ssid, securitykey)

        pygame.display.update()
