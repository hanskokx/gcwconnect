#!/usr/bin/env python

#	wificonfig.py
#
#	Requires: pygame
#			
#	Copyright (c) 2013 Hans Kokx
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

import subprocess as SU
import sys, time, os, shutil
import pygame
from pygame.locals import *

# What is our wireless interface?
wlan = "wlan0"

# Create paths, if necessary
confdir = "/boot/local/home/.gcwconnect/"
if not os.path.exists(confdir):
	os.makedirs(confdir)

sysconfdir = "/usr/local/etc/network/"
if not os.path.exists(sysconfdir):
	os.makedirs(sysconfdir)

if not pygame.display.get_init():
	pygame.display.init()

if not pygame.font.get_init():
	pygame.font.init()

networks = {}
uniqssids = {}
currentssid = ""

## Interface management
def ifdown():
	command = ['ifdown', wlan]
	output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()
def ifup():
	while checkinterfacestatus() == '':
		command = ['ifup', wlan]
		output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()

	wlanstatus = ""
	currentssid = getcurrentssid()
	if not checkinterfacestatus() == "offline":
		if not currentssid == "unassociated":
			modal("Connected!","false","true")
	
def getwlanip():
	ip = ""
	command = ['ifconfig', wlan]
	output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()

	for line in output:
		if line.strip().startswith("inet addr"):
			ip = str.strip(line[line.find('inet addr')+len('inet addr"'):line.find('Bcast')+len('Bcast')].rstrip('Bcast'))

	return ip
def checkinterfacestatus():
	interface = "" # set default assumption of interface status
	ip = ""
	command = ['ifconfig']
	output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()

	for line in output:
		if line.strip().startswith(wlan):
			ip = getwlanip()
			if ip:
				interface = ip

	return interface
def getnetworks(): # Run iwlist to get a list of networks in range
	modal("Scanning...","false")
	command = ['ifconfig', wlan, 'up']
	output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()
	command = ['iwlist', wlan, 'scan']
	output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()
	for item in output:

		if item.strip().startswith('Cell'):
			# network is the current list corresponding to a MAC address {MAC:[]}
			network = networks.setdefault(parsemac(item), dict())

		elif item.strip().startswith('ESSID:'):
			network["ESSID"] = (parseessid(item))

		elif item.strip().startswith('IE:') and not item.strip().startswith('IE: Unknown') or item.strip().startswith('Encryption key:'):
			network["Encryption"] = (parseencryption(item))

		elif item.strip().startswith('Quality='):
			network["Quality"] = (parsequality(item))
		# Now the loop is over, we will probably find a MAC address and a new "network" will be created.
	redraw()
	return networks
def listuniqssids():
	menu_position = 0
	uniqssid = {}
	uniqssids = {}

	for network, detail in networks.iteritems():
			if detail['ESSID'] not in uniqssids and detail['ESSID'] and detail['ESSID']:
				uniqssid = uniqssids.setdefault(menu_position, {})
				uniqssid["Network"] = detail
				menu_position += 1

	return uniqssids

## Parsing iwlist output for various components
def parsemac(macin):
	mac = str.strip(macin[macin.find("Address:")+len("Address: "):macin.find("\n")+len("\n")])
	return mac
def parseessid(essid):
		essid = str.strip(essid[essid.find('ESSID:"')+len('ESSID:"'):essid.find('"\n')+len('"\n')].rstrip('"\n'))
		return essid
def parsequality(quality):
	quality = quality[quality.find("Quality=")+len("Quality="):quality.find(" S")+len(" S")].rstrip(" S")
	return quality
def parseencryption(encryption):
	encryption = str.strip(encryption)

 	if encryption.startswith('Encryption key:off'):
	 	encryption = "none"

	elif encryption.startswith('Encryption key:on'):
		encryption = "Encrypted (unknown)"

	elif encryption.startswith("IE: WPA"):
		encryption = "wpa"

	elif encryption.startswith("IE: IEEE 802.11i/WPA2"):
		encryption = "wpa2"

	else:
		encryption = "wep"

	return encryption

## Draw interface elements
def drawlogobar(): # Set up the menu bar
	pygame.draw.rect(surface, (84,84,84), (0,0,320,32))
	pygame.draw.line(surface, (255, 255, 255), (0, 33), (320, 33))
def drawlogo():
	gcw = "GCW"
	zero = "Connect"
	# wireless = "Wireless"
	# configuration = "configuration"

	gcw_font = pygame.font.Font('data/gcwzero.ttf', 24)

	text1 = gcw_font.render(gcw, True, (255, 255, 255), (84,84,84))
	text2 = gcw_font.render(zero, True, (153, 0, 0), (84,84,84))
	# text3 = pygame.font.SysFont(None, 16).render(wireless, True, (255, 255, 255), (84,84,84))
	# text4 = pygame.font.SysFont(None, 16).render(configuration, True, (255, 255, 255), (84,84,84))

	logo_text = text1.get_rect()
	logo_text.topleft = (8, 6)
	surface.blit(text1, logo_text)

	logo_text = text2.get_rect()
	logo_text.topleft = (98, 6)
	surface.blit(text2, logo_text)

	# logo_text = text3.get_rect()
	# logo_text.topleft = (272, 5)
	# surface.blit(text3, logo_text)

	# logo_text = text4.get_rect()
	# logo_text.topleft = (245, 18)
	# surface.blit(text4, logo_text)
def drawstatusbar(): # Set up the status bar
	pygame.draw.rect(surface, (84,84,84), (0,224,320,16))
	pygame.draw.line(surface, (255, 255, 255), (0, 223), (320, 223))
def drawinterfacestatus(): # Interface status badge
	wlanstatus = ""
	currentssid = getcurrentssid()
	if not checkinterfacestatus() == '':
		if currentssid == "unassociated":
			wlanstatus = wlan+" is disconnected."
		elif not currentssid == "unassociated":
			wlanstatus = currentssid
	else:
		wlanstatus = wlan+" is off."

	wlantext = pygame.font.SysFont(None, 16).render(wlanstatus, True, (255, 255, 255), (84,84,84))
	wlan_text = wlantext.get_rect()
	wlan_text.topleft = (4, 227)
	surface.blit(wlantext, wlan_text)

	if not checkinterfacestatus() == "not connected":
		text = pygame.font.SysFont(None, 16).render(checkinterfacestatus(), True, (153, 0, 0), (84,84,84))
		interfacestatus_text = text.get_rect()
		interfacestatus_text.topright = (315, 227)
		surface.blit(text, interfacestatus_text)
def getcurrentssid(): # What network are we connected to?
	command = ['iwconfig', wlan]
	output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()

	for line in output:
		if line.strip().startswith(wlan):
			ssid = str.strip(line[line.find('ESSID')+len('ESSID:"'):line.find('Nickname:')+len('Nickname:')].rstrip(' Nickname:').rstrip('"'))

	return ssid

def redraw():
	surface.fill((41,41,41))
	drawlogobar()
	drawlogo()
	mainmenu()
	if not wirelessmenuexists == "false":
		wirelessmenu.draw()
	drawstatusbar()
	drawinterfacestatus()
	pygame.display.update()
def modal(text,wait="true",timeout="false"): # Draw a modal
	dialog = pygame.draw.rect(surface, (84,84,84), (96,88,128,64))
	pygame.draw.rect(surface, (255,255,255), (94,86,130,66), 2)

	text = pygame.font.SysFont(None, 16).render(text, True, (255, 255, 255), (84,84,84))
	modal_text = text.get_rect()
	modal_text.center = dialog.center

	surface.blit(text, modal_text)
	pygame.display.update()

	if not wait == "true" and timeout == "true":
		time.sleep(2)
		redraw()

	while wait == "true":
		for event in pygame.event.get():
			if event.key == K_LCTRL:
				redraw()
				wait = "false"
def writeconfig(): # Write wireless configuration to disk
	f = open(ssidconfig, "a")
	f.write('WLAN_ESSID="'+uniq[wirelessmenu.get_position()]['Network']['ESSID']+'"\n')
	f.write('WLAN_MODE="managed"\n')
	f.write('WLAN_ENCRYPTION="'+uniq[wirelessmenu.get_position()]['Network']['Encryption']+'"\n')
	f.write('WLAN_PASSPHRASE="WPA2-key"\n') # TODO: on-screen keyboard for manual key entry
	f.write('WLAN_DRIVER="wext"\n')
	f.write('WLAN_DHCP_RETRIES=20\n')
	f.close()
def connect(): # Connect to a network
	oldconf = ssidconfig
	newconf = sysconfdir +"config-wlan0.conf"
	shutil.copy2(ssidconfig, newconf)
	ifdown()
	ifup()
class Menu:
	font_size = 24
	font = pygame.font.SysFont
	dest_surface = pygame.Surface
	canvas_color = (41,41,41)

	def __init__(self):
		self.menu = []
		self.field = []
		self.selected_item = 0
		self.selection_position = (0,0)
		self.menu_width = 0
		self.menu_height = 0
		self.number_of_fields = 0
		self.selection_color = (153,0,0)
		self.text_color =  (255,255,255)

	class Pole:
		text = ''
		pole = pygame.Surface
		pole_rect = pygame.Rect
		selection_rect = pygame.Rect

	def move_menu(self, top, left):
		self.selection_position = (top,left) 

	def set_colors(self, text, selection, background):
		self.canvas_color = background
		self.text_color =  text
		self.selection_color = selection
		
	def set_fontsize(self,font_size):
		self.font_size = font_size
		
	def set_font(self, path):
		self.font_path = path
		
	def get_position(self):
		return self.selected_item
	
	def init(self, menu, dest_surface):
		self.menu = menu
		self.dest_surface = dest_surface
		self.number_of_fields = len(self.menu)
		self.create_structure()		
		
	def draw(self,move=0):
		if move:
			self.selected_item += move 
			if self.selected_item == -1:
				self.selected_item = self.number_of_fields - 1
			self.selected_item %= self.number_of_fields
		menu = pygame.Surface((self.menu_width, self.menu_height))
		menu.fill(self.canvas_color)
		selection_rect = self.field[self.selected_item].selection_rect
		pygame.draw.rect(menu,self.selection_color,selection_rect)

		for i in xrange(self.number_of_fields):
			menu.blit(self.field[i].pole,self.field[i].pole_rect)
		self.dest_surface.blit(menu,self.selection_position)
		return self.selected_item

	def create_structure(self):
		shift = 0
		self.menu_height = 0
		self.font = pygame.font.SysFont('Arial', self.font_size)
		for i in xrange(self.number_of_fields):
			self.field.append(self.Pole())
			self.field[i].text = self.menu[i]
			self.field[i].pole = self.font.render(self.field[i].text, 1, self.text_color)

			self.field[i].pole_rect = self.field[i].pole.get_rect()
			shift = int(self.font_size * 0.2)

			height = self.field[i].pole_rect.height
			self.field[i].pole_rect.left = shift
			self.field[i].pole_rect.top = shift+(shift*2+height)*i

			width = self.field[i].pole_rect.width+shift*2
			height = self.field[i].pole_rect.height+shift*2			
			left = self.field[i].pole_rect.left-shift
			top = self.field[i].pole_rect.top-shift

			self.field[i].selection_rect = (left,top ,width, height)
			if width > self.menu_width:
					self.menu_width = width
			self.menu_height += height
		x = self.dest_surface.get_rect().centerx - self.menu_width / 2
		y = self.dest_surface.get_rect().centery - self.menu_height / 2
		mx, my = self.selection_position
		self.selection_position = (x+mx, y+my) 
def swapmenu(active_menu):	
	if active_menu == "main":
		active_menu = "ssid"
		menu.set_colors((128,128,128), (84,84,84), (41,41,41))
		wirelessmenu.set_colors((255,255,255), (153,0,0), (41,41,41))
		redraw()
	elif active_menu == "ssid":
		active_menu = "main"
		menu.set_colors((255,255,255), (153,0,0), (41,41,41))
		wirelessmenu.set_colors((128,128,128), (84,84,84), (41,41,41))
		redraw()
	return active_menu

wirelessmenu = Menu()
wirelessmenuexists = "false"
menu = Menu()
def mainmenu():
	#menu.set_colors((255,255,255), (0,0,255), (0,0,0))#optional
	#menu.set_fontsize(64)#optional
	#menu.move_menu(100, 99)#optional
	menu.init(['Scan', 'Toggle Wifi', 'Quit'], surface)
	menu.move_menu(16, 96)
	menu.draw()

if __name__ == "__main__":
	import sys
	surface = pygame.display.set_mode((320,240))
	surface.fill((41,41,41))
	pygame.mouse.set_visible(False)
	pygame.key.set_repeat(199,69) #(delay,interval)
	redraw()
	active_menu = "main"

	while 1:
		for event in pygame.event.get():
			## GCW-Zero keycodes:
			# A = K_LCTRL
			# B = K_LALT
			# X = K_LSHIFT
			# Y = K_SPACE
			# L = K_TAB
			# R = K_BACKSPACE
			# start = K_RETURN
			# select = K_ESCAPE
			# power up = KEY_POWER
			# power down = KEY_PAUSE

			if event.type == QUIT:
				pygame.display.quit()
				sys.exit()

			elif event.type == KEYDOWN:
				if event.key == K_UP: # Arrow up the menu
					if active_menu == "main":
						menu.draw(-1)
					if active_menu == "ssid":
						wirelessmenu.draw(-1)
				if event.key == K_DOWN: # Arrow down the menu
					if active_menu == "main":
						menu.draw(1)
					if active_menu == "ssid":
						wirelessmenu.draw(1)

				if event.key == K_LEFT or event.key == K_RIGHT:
					if not wirelessmenuexists == "false":
						active_menu = swapmenu(active_menu)

				if event.key == K_LCTRL:
					# Main menu
					if active_menu == "main":
						if menu.get_position() == 0: # Scan menu
							getnetworks()
							uniq = listuniqssids()
							counter = 0

							wirelessitems = []
							wirelessmenu.set_fontsize(14)

							for x, y in uniq.iteritems():
								for label, network in y.iteritems():
									wirelessitems.append(network['ESSID'])

							wirelessmenu.init(wirelessitems, surface)
							wirelessmenu.move_menu(128, 36)
							wirelessmenu.draw()
							wirelessmenuexists = "true"
							active_menu = swapmenu('main')

						if menu.get_position() == 1: # Toggle wifi
							if not checkinterfacestatus():
								modal("Connecting...","false")
								ifup()
								redraw()
							else:
								ifdown()
								redraw()

						if menu.get_position() == 2: # Quit menu
							pygame.display.quit()
							sys.exit()

					# SSID menu		
					elif active_menu == "ssid":
						netconfdir = confdir+"networks/"
						if not os.path.exists(netconfdir):
							os.makedirs(netconfdir)
						ssidconfig = netconfdir +uniq[wirelessmenu.get_position()]['Network']['ESSID'] +".conf"
						if not os.path.exists(ssidconfig):
							writeconfig()
						modal("Connecting...","false")
						connect()
						drawinterfacestatus()

		pygame.display.update()
