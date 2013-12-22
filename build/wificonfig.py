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


'''

TODO list:

* Add in hostapd/ap configuration options for device to device connections

'''


import subprocess as SU
import sys, time, os, shutil, re
import pygame
from pygame.locals import *
from os import listdir

# What is our wireless interface?
wlan = "wlan0"

darkbg = (41, 41, 41)
lightbg = (84, 84, 84)
activeselbg = (153, 0, 0)
inactiveselbg = (84, 84, 84)
activetext = (255, 255, 255)
inactivetext = (128, 128, 128)
lightgrey = (200,200,200)

## That's it for options. Everything else below shouldn't be edited.
confdir = os.environ['HOME'] + "/.gcwconnect/"
netconfdir = confdir+"networks/"
sysconfdir = "/usr/local/etc/network/"

surface = pygame.display.set_mode((320,240))
keyboard = ''
selected_key = ''
maxrows = ''
maxcolumns = ''
passphrase = ''
active_menu = ''

## Initialize the display, for pygame
if not pygame.display.get_init():
	pygame.display.init()
if not pygame.font.get_init():
	pygame.font.init()

surface.fill(darkbg)
pygame.mouse.set_visible(False)
pygame.key.set_repeat(199,69) #(delay,interval)

## File management
def createpaths(): # Create paths, if necessary
	if not os.path.exists(confdir):
		os.makedirs(confdir)
	if not os.path.exists(netconfdir):
		os.makedirs(netconfdir)
	if not os.path.exists(sysconfdir):
		os.makedirs(sysconfdir)

## Interface management
def ifdown(iface):
	with open(os.devnull, "w") as fnull:
		return SU.Popen(['ifdown', iface], stderr = fnull).wait() != 0

def ifup(iface):
	with open(os.devnull, "w") as fnull:
		return SU.Popen(['ifup', iface], \
				stdout=fnull, stderr=fnull).wait() == 0

# Returns False if the interface was previously enabled
def enableiface(iface):
	check = checkinterfacestatus(iface)
	if check:
		return False

	modal("Enabling WiFi...")
	drawinterfacestatus()
	pygame.display.update()

	with open(os.devnull, "w") as fnull:
		SU.Popen(['rfkill', 'unblock', 'wlan'], \
				stderr=fnull, stdout=fnull).wait()
		while True:
			if SU.Popen(['ifconfig', iface, 'up'], \
					stderr=fnull, stdout=fnull).wait() == 0:
				break
			time.sleep(0.1);
	return True

def disableiface(iface):
	with open(os.devnull, "w") as fnull:
		SU.Popen(['rfkill', 'block', 'wlan'],
				stderr=fnull, stdout=fnull).wait()

def getip(iface):
	with open(os.devnull, "w") as fnull:
		output = SU.Popen(['ifconfig', iface], \
				stderr=fnull, stdout=SU.PIPE).stdout.readlines()

	for line in output:
		if line.strip().startswith("inet addr"):
			return str.strip( \
					line[line.find('inet addr')+len('inet addr"') :\
					line.find('Bcast')+len('Bcast')].rstrip('Bcast'))

def getcurrentssid(iface): # What network are we connected to?
	if not checkinterfacestatus(iface):
		return None

	with open(os.devnull, "w") as fnull:
		output = SU.Popen(['iwconfig', iface], \
				stdout=SU.PIPE, stderr = fnull).stdout.readlines()
	for line in output:
		if line.strip().startswith(iface):
			ssid = str.strip(line[line.find('ESSID')+len('ESSID:"'):line.find('Nickname:')+len('Nickname:')].rstrip(' Nickname:').rstrip('"'))
	return ssid

def checkinterfacestatus(iface):
	return getip(iface) != None

def connect(iface): # Connect to a network
	shutil.copy2(netconfdir+ssidconfig+".conf", \
			sysconfdir+"config-"+iface+".conf")

	if checkinterfacestatus(iface):
		disconnect(iface)

	modal("Connecting...")
	if not ifup(wlan):
		modal('Connection failed!', wait=True)
		return False

	modal('Connected!', timeout=True)
	pygame.display.update()
	drawstatusbar()
	drawinterfacestatus()
	return True

def disconnect(iface):
	if checkinterfacestatus(iface):
		modal("Disconnecting...")
		ifdown(iface)

def getnetworks(iface): # Run iwlist to get a list of networks in range
	wasnotenabled = enableiface(iface)
	modal("Scanning...")

	with open(os.devnull, "w") as fnull:
		output = SU.Popen(['iwlist', iface, 'scan'] \
				, stdout=SU.PIPE, stderr=fnull).stdout.readlines()
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

	if wasnotenabled:
		disableiface(iface)
	return networks

def listuniqssids():
	menuposition = 0
	uniqssid = {}
	uniqssids = {}

	for network, detail in networks.iteritems():
			if detail['ESSID'] not in uniqssids and detail['ESSID']:
				uniqssid = uniqssids.setdefault(detail['ESSID'], {})
				uniqssid["Network"] = detail
				uniqssid["Network"]["menu"] = menuposition
				uniqssid["Network"]["Encryption"] = detail['Encryption']
				menuposition += 1
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
	if len(quality) < 1:
		quality = '0/100'
	return quality

def parseencryption(encryption):
	encryption = str.strip(encryption)

	if encryption.startswith('Encryption key:off'):
	 	encryption = "none"
	elif encryption.startswith('Encryption key:on'):
		encryption = "wep"
	elif encryption.startswith("IE: WPA"):
		encryption = "wpa"
	elif encryption.startswith("IE: IEEE 802.11i/WPA2"):
		encryption = "wpa2"
	else:
		encryption = "Encrypted (unknown)"
	return encryption

## Saved Networks menu
def getsavednets():
	uniqssid = {}
	uniqssids = {}
	menu = 1
	configs = [ f for f in listdir(netconfdir) ]
	for x in configs:
		try:
			x = re.sub(r'[\s"\\]', '', x).strip()
		except:
			pass
		conf = netconfdir+x
		x = x.split(".conf")[:-1][0]

		with open(conf) as f:
			for line in f:
				if "WLAN_PASSPHRASE" in line:
					key = str.strip(line[line.find('WLAN_PASSPHRASE="')\
						+len('WLAN_PASSPHRASE="'):line.find('"\n')+len('"\n')].rstrip('"\n'))

		uniqssid=uniqssids.setdefault(x, {'Network': {'ESSID': x, 'Key': key, 'menu': menu}})
		menu += 1
	uniq = uniqssids
	return uniq

## Draw interface elements
class hint:
	def __init__(self, button, text, x, y, bg=darkbg):
		self.button = button
		self.text = text
		self.x = x
		self.y = y
		self.bg = bg
		self.drawhint()

	def drawhint(self):
		color = (255,255,255)
		yellow = (128, 128, 0)
		blue = (0, 0, 128)
		red = (128, 0, 0)
		green = (0, 128, 0)
		black = (0, 0, 0)
		white = (255, 255, 255)

		if self.button == "select" or self.button == "start":
			if self.button == "select":
				pygame.draw.rect(surface, black, (self.x, self.y, 34, 5))
				pygame.draw.circle(surface, black, (self.x+5, self.y+5), 5)
				pygame.draw.circle(surface, black, (self.x+29, self.y+5), 5)


			elif self.button == "start":
				pygame.draw.rect(surface, black, (self.x, self.y+5, 34, 5))
				pygame.draw.circle(surface, black, (self.x+5, self.y+5), 5)
				pygame.draw.circle(surface, black, (self.x+29, self.y+5), 5)
			
			button = pygame.draw.rect(surface, black, (self.x+5, self.y, 25, 10))
			text = pygame.font.Font(None, 10).render(self.button.upper(), True, (255, 255, 255), black)
			buttontext = text.get_rect()
			buttontext.center = button.center
			surface.blit(text, buttontext)

			labelblock = pygame.draw.rect(surface, self.bg, (self.x+40,self.y,25,14))
			labeltext = pygame.font.SysFont(None, 12).render(self.text, True, (255, 255, 255), self.bg)
			surface.blit(labeltext, labelblock)

		elif self.button == "a" \
			or self.button == "b" \
			or self.button == "x" \
			or self.button == "y":
			
			if self.button == "a":
				color = green
			elif self.button == "b":
				color = blue
			elif self.button == "x":
				color = red
			elif self.button == "y":
				color = yellow

			labelblock = pygame.draw.rect(surface, self.bg, (self.x+10,self.y,35,14))
			labeltext = pygame.font.SysFont(None, 12).render(self.text, True, (255, 255, 255), self.bg)
			surface.blit(labeltext, labelblock)

			button = pygame.draw.circle(surface, color, (self.x,self.y+4), 5) # (x, y)
			text = pygame.font.SysFont(None, 10).render(self.button.upper(), True, (255, 255, 255), color)
			buttontext = text.get_rect()
			buttontext.center = button.center
			surface.blit(text, buttontext)

		elif self.button == "left" \
			or self.button == "right" \
			or self.button == "up" \
			or self.button == "down":

			# Vertical
			pygame.draw.rect(surface, black, (self.x+5, self.y-1, 4, 12))
			pygame.draw.rect(surface, black, (self.x+6, self.y-2, 2, 14))

			# Horizontal
			pygame.draw.rect(surface, black, (self.x+1, self.y+3, 12, 4))
			pygame.draw.rect(surface, black, (self.x, self.y+4, 14, 2))

			if self.button == "left":
				pygame.draw.rect(surface, white, (self.x+2, self.y+4, 3, 2))
			elif self.button == "right":
				pygame.draw.rect(surface, white, (self.x+9, self.y+4, 3, 2))
			elif self.button == "up":
				pygame.draw.rect(surface, white, (self.x+6, self.y+1, 2, 3))
			elif self.button == "down":
				pygame.draw.rect(surface, white, (self.x+6, self.y+7, 2, 3))

			labelblock = pygame.draw.rect(surface, self.bg, (self.x+20,self.y,35,14))
			labeltext = pygame.font.SysFont(None, 12).render(self.text, True, (255, 255, 255), self.bg)
			surface.blit(labeltext, labelblock)

def drawlogobar(): # Set up the menu bar
	pygame.draw.rect(surface, lightbg, (0,0,320,32))
	pygame.draw.line(surface, (255, 255, 255), (0, 33), (320, 33))

def drawlogo():
	gcw = "GCW"
	zero = "Connect"
	# wireless = "Wireless"
	# configuration = "configuration"

	gcw_font = pygame.font.Font('./data/gcwzero.ttf', 24)

	text1 = gcw_font.render(gcw, True, (255, 255, 255), lightbg)
	text2 = gcw_font.render(zero, True, (153, 0, 0), lightbg)

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
	pygame.draw.rect(surface, lightbg, (0,224,320,16))
	pygame.draw.line(surface, (255, 255, 255), (0, 223), (320, 223))
	wlantext = pygame.font.SysFont(None, 16).render("...", True, (255, 255, 255), lightbg)
	wlan_text = wlantext.get_rect()
	wlan_text.topleft = (4, 227)
	surface.blit(wlantext, wlan_text)

def drawinterfacestatus(): # Interface status badge
	wlanstatus = checkinterfacestatus(wlan)
	if not wlanstatus: 
		wlanstatus = wlan+" is off."
	else:
		wlanstatus = getcurrentssid(wlan)

	wlantext = pygame.font.SysFont(None, 16).render(wlanstatus, True, (255, 255, 255), lightbg)
	wlan_text = wlantext.get_rect()
	wlan_text.topleft = (4, 227)
	surface.blit(wlantext, wlan_text)

	if checkinterfacestatus(wlan):
		text = pygame.font.SysFont(None, 16).render(getip(wlan), True, (153, 0, 0), lightbg)
		interfacestatus_text = text.get_rect()
		interfacestatus_text.topright = (315, 227)
		surface.blit(text, interfacestatus_text)

def redraw():
	surface.fill(darkbg)
	drawlogobar()
	drawlogo()
	mainmenu()
	if wirelessmenu is not None:
		wirelessmenu.draw()
		pygame.draw.rect(surface, darkbg, (0, 208, 320, 16))
		hint("select", "Edit", 4, 210)
		hint("a", "Connect", 75, 210)
		hint("b", "/", 130, 210)
		hint("left", "Back", 145, 210)
	if active_menu == "main":
		pygame.draw.rect(surface, darkbg, (0, 208, 320, 16))
		hint("a", "Select", 8, 210)
	if active_menu == "saved":
		hint("y", "Forget", 195, 210)

	drawstatusbar()
	drawinterfacestatus()
	pygame.display.update()

def modal(text, wait=False, timeout=False, query=False):
	dialog = pygame.draw.rect(surface, lightbg, (64,88,192,72))
	pygame.draw.rect(surface, (255,255,255), (62,86,194,74), 2)

	text = pygame.font.SysFont(None, 16).render(text, True, (255, 255, 255), lightbg)
	modal_text = text.get_rect()
	modal_text.center = dialog.center

	surface.blit(text, modal_text)
	pygame.display.update()

	if wait:
		abutton = hint("a", "Continue", 205, 145, lightbg)
		pygame.display.update()
	elif timeout:
		time.sleep(2.5)
		redraw()
	elif query:
		abutton = hint("a", "Confirm", 150, 145, lightbg)
		bbutton = hint("b", "Cancel", 205, 145, lightbg)
		pygame.display.update()
		while True:
			for event in pygame.event.get():
				if event.type == KEYDOWN:
					if event.key == K_LCTRL:
						return True
					elif event.key == K_LALT:
						return



	if not wait:
		return

	while True:
		for event in pygame.event.get():
			if event.type == KEYDOWN and event.key == K_LCTRL:
				redraw()
				return

## Connect to a network
def writeconfig(): # Write wireless configuration to disk
	global passphrase
	global encryption
	try:
		encryption
	except NameError:
		encryption = uniq[ssid]['Network']['Encryption']

	if passphrase:
		if passphrase == "none":
			passphrase = ""
	conf = netconfdir+ssidconfig+".conf"
	f = open(conf, "w")
	f.write('WLAN_ESSID="'+ssid+'"\n')
	f.write('WLAN_ENCRYPTION="'+encryption+'"\n')
	f.write('WLAN_PASSPHRASE="'+passphrase+'"\n')
	f.write('WLAN_DHCP_RETRIES=20\n')
	f.close()

## Input methods
def getkeys(board):
	def qwertyNormal():
		keyarray = {}
		keyboard = {}
		global maxrows
		global maxcolumns
		maxrows = 4
		maxcolumns = 13
		keys = 	'`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=',\
				'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\',\
				'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '', '',\
				'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', '', '', ''
		row = 0
		column = 0
		keyid = 0
		for k in keys:
			keyarray = keyboard.setdefault(keyid, {})
			keyarray["key"] = k

			if column <= 12:
				keyarray["column"] = column
				keyarray["row"] = row
				column += 1
			else:
				row += 1
				column = 0
				keyarray["column"] = column
				keyarray["row"] = row
				column += 1
			
			keyid += 1
		return keyboard

	def qwertyShift():
		keyarray = {}
		keyboard = {}
		global maxrows
		global maxcolumns
		maxrows = 4
		maxcolumns = 13
		keys = 	'~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+',\
				'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '|',\
				'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', '', '',\
				'Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?', '', '', ''
		row = 0
		column = 0
		keyid = 0
		for k in keys:
			keyarray = keyboard.setdefault(keyid, {})
			keyarray["key"] = k

			if column <= 12:
				keyarray["column"] = column
				keyarray["row"] = row
				column += 1
			else:
				row += 1
				column = 0
				keyarray["column"] = column
				keyarray["row"] = row
				column += 1
			
			keyid += 1
		return keyboard

	def wep():
		keyarray = {}
		keyboard = {}
		global maxrows
		global maxcolumns
		maxrows = 4
		maxcolumns = 4
		keys = 	'1', '2', '3', '4', \
				'5', '6', '7', '8', \
				'9', '0', 'A', 'B', \
				'C', 'D', 'E', 'F'
		row = 0
		column = 0
		keyid = 0
		for k in keys:
			keyarray = keyboard.setdefault(keyid, {})
			keyarray["key"] = k

			if column <= 3:
				keyarray["column"] = column
				keyarray["row"] = row
				column += 1
			else:
				row += 1
				column = 0
				keyarray["column"] = column
				keyarray["row"] = row
				column += 1
			
			keyid += 1
		return keyboard

	def encryption():
		keyarray = {}
		keyboard = {}
		global maxrows
		global maxcolumns
		maxrows = 1
		maxcolumns = 3
		keys = 	'None', 'WEP', 'WPA/WPA2'
		row = 0
		column = 0
		keyid = 0
		for k in keys:
			keyarray = keyboard.setdefault(keyid, {})
			keyarray["key"] = k

			if column <= 3:
				keyarray["column"] = column
				keyarray["row"] = row
				column += 1
			else:
				row += 1
				column = 0
				keyarray["column"] = column
				keyarray["row"] = row
				column += 1
			
			keyid += 1
		return keyboard

	if board == "qwertyNormal":
		k = qwertyNormal()
	elif board == "qwertyShift":
		k = qwertyShift()
	elif board == "wep":
		k = wep()
	elif board == "encryption":
		k = encryption()
	return k

class key:
	def __init__(self):
		self.key = []
		self.selection_color = activeselbg
		self.text_color = activetext
		self.selection_position = (0,0)
		self.selected_item = 0

	def init(self, key, row, column):
		self.key = key
		self.row = row
		self.column = column
		self.drawkey()

	def drawkey(self):
		key_width = 16
		key_height = 16

		top = 136 + self.row * 20
		left = 32 + self.column * 20

		if len(self.key) > 1:
			key_width = 36
		keybox = pygame.draw.rect(surface, lightbg, (left,top,key_width,key_height))
		text = pygame.font.SysFont(None, 16).render(self.key, True, (255, 255, 255), lightbg)
		label = text.get_rect()
		label.center = keybox.center
		surface.blit(text, label)

class radio:
	def __init__(self):
		self.key = []
		self.selection_color = activeselbg
		self.text_color = activetext
		self.selection_position = (0,0)
		self.selected_item = 0

	def init(self, key, row, column):
		self.key = key
		self.row = row
		self.column = column
		self.drawkey()

	def drawkey(self):
		key_width = 64
		key_height = 16

		top = 136 + self.row * 20
		left = 32 + self.column * 100

		if len(self.key) > 1:
			key_width = 64
		radiobutton = pygame.draw.circle(surface, (255,255,255), (left, top), 8, 2)
		text = pygame.font.SysFont(None, 16).render(self.key, True, (255, 255, 255), darkbg)
		label = text.get_rect()
		label.left = radiobutton.right + 8
		label.top = radiobutton.top + 4
		surface.blit(text, label)

def getSSID():
	global passphrase
	displayinputlabel("ssid")
	drawkeyboard("qwertyNormal")
	getinput("qwertyNormal", "ssid")
	ssid = passphrase
	passphrase = ''
	return ssid

def drawEncryptionType():
	# Draw top background 
	pygame.draw.rect(surface, darkbg, (0,100,320,140))

	# Draw footer
	pygame.draw.rect(surface, lightbg, (0,224,320,16))
	pygame.draw.line(surface, (255, 255, 255), (0, 223), (320, 223))
	hint("select", "Cancel", 4, 227, lightbg)
	hint("a", "Enter", 285, 227, lightbg)

	# Draw the keys
	k = getkeys("encryption")
	z = radio()

	for x, y in k.iteritems():
		if y['key']:
			z.init(y['key'],y['row'],y['column'])

	pygame.display.update()

def chooseencryption(keyboard, direction):
	def getcurrentkey(keyboard, pos):
		keys = getkeys(keyboard)
		for x in keys.iteritems():
			for item in x:
				if x[1]['column'] == pos[0]:
					currentkey = x[1]['key']
		return currentkey

	def highlightradio(keyboard, pos='[0,0]'):
		drawEncryptionType()
		pygame.display.update()

		x = 32 + (pos[0] * 100)
		y = 136

		list = [ \
					(x, y), \
					(x + 16, y), \
					(x + 16, y + 16), \
					(x, y + 16), \
					(x, y) \
				]

		pygame.draw.circle(surface, activeselbg, (x, y), 6)
		pygame.display.update()

	global maxcolumns
	global selected_key
	encryption = ''

	if direction == "left":
		if selected_key[0] <= 0:
			selected_key[0] = 0
		elif not getcurrentkey(keyboard, (selected_key[0] - 1, selected_key[1])):
			selected_key[0] = selected_key[0]
		else:
			selected_key[0] = selected_key[0] - 1

	elif direction == "right":
		if selected_key[0] >= maxcolumns - 1:
			selected_key[0] = maxcolumns - 1
		elif not getcurrentkey(keyboard, (selected_key[0] + 1, selected_key[1])):
			selected_key[0] = selected_key[0]
		else:
			selected_key[0] = selected_key[0] + 1

	elif direction == "select":
		encryption = getcurrentkey(keyboard, selected_key)
	
	elif direction == "init":
		selected_key = [0,0]
		highlightradio(keyboard, selected_key)

	highlightradio(keyboard, selected_key)
	return encryption

def getEncryptionType():
	chooseencryption("encryption", "init")
	while True:
		for event in pygame.event.get():
			if event.type == KEYDOWN:
				if event.key == K_LEFT:		# Move cursor left
					chooseencryption("encryption", "left")
				if event.key == K_RIGHT:	# Move cursor right
					chooseencryption("encryption", "right")
				if event.key == K_LCTRL:	# A button
					return chooseencryption("encryption", "select")
				if event.key == K_ESCAPE:	# Select key
					return 'cancel'

def drawkeyboard(board):
	# Draw keyboard background 
	pygame.draw.rect(surface, darkbg, (0,100,320,140))

	# Draw bottom background
	pygame.draw.rect(surface, lightbg, (0,224,320,16))
	pygame.draw.line(surface, (255, 255, 255), (0, 223), (320, 223))

	hint("select", "Cancel", 4, 227, lightbg)
	hint("start", "Finish", 75, 227, lightbg)
	hint("x", "Delete", 155, 227, lightbg)
	if not board == "wep":
		hint("y", "Shift", 200, 227, lightbg)
		hint("b", "Space", 240, 227, lightbg)

	else:
		hint("y", "Full KB", 200, 227, lightbg)

	hint("a", "Enter", 285, 227, lightbg)

	# Draw the keys

	k = getkeys(board)
	z = key()

	for x, y in k.iteritems():
		if y['key']:
			z.init(y['key'],y['row'],y['column'])

	pygame.display.update()
	return keyboard

def getinput(board, kind, ssid=""):
	selectkey(board, kind)
	return softkeyinput(board, kind, ssid)

def softkeyinput(keyboard, kind, ssid):
	global passphrase
	global encryption
	global securitykey

	while True:
		for event in pygame.event.get():

			if event.type == KEYDOWN:
				if event.key == K_RETURN:		# finish input
					selectkey(keyboard, kind, "enter")
					redraw()
					if ssid == '':
						return False
					writeconfig()
					connect(wlan)
					return True

				if event.key == K_UP:		# Move cursor up
					selectkey(keyboard, kind, "up")
				if event.key == K_DOWN:		# Move cursor down
					selectkey(keyboard, kind, "down")
				if event.key == K_LEFT:		# Move cursor left
					selectkey(keyboard, kind, "left")
				if event.key == K_RIGHT:	# Move cursor right
					selectkey(keyboard, kind, "right")
				if event.key == K_LCTRL:	# A button
					selectkey(keyboard, kind, "select")
				if event.key == K_LALT:		# B button
					selectkey(keyboard, kind, "space")
				if event.key == K_SPACE:	# Y button (swap keyboards)
					# if not uniq[ssid]['Network']['Encryption'] == "wpa2" \
					# 	or not uniq[ssid]['Network']['Encryption'] == "wpa":
					# 	uniq[ssid]['Network']['Encryption'] = "wpa2"
						# TESTING DEBUG
						# This may work, or it may not. Will need to revisit it.
						# TODO

					if keyboard == "qwertyNormal":
						keyboard = "qwertyShift"
						drawkeyboard(keyboard)
						selectkey(keyboard, kind, "swap")
					elif keyboard == "qwertyShift":
						keyboard = "qwertyNormal"
						drawkeyboard(keyboard)
						selectkey(keyboard, kind, "swap")
					else:
						keyboard = "qwertyNormal"
						drawkeyboard(keyboard)
						selectkey(keyboard, kind, "swap")
					encryption = "wpa"
				if event.key == K_LSHIFT:	# X button
					selectkey(keyboard, kind, "delete")
				if event.key == K_ESCAPE:	# Select key
					passphrase = ''
					try:
						encryption
					except NameError:
						pass
					else:
						del encryption

					try:
						securitykey
					except NameError:
						pass
					else:
						del securitykey
					redraw()
					return False

def displayinputlabel(kind, size=24): # Display passphrase on screen

	if kind == "ssid":
		# Draw SSID and encryption type labels
		labelblock = pygame.draw.rect(surface, (255,255,255), (0,35,320,20))
		labeltext = pygame.font.SysFont(None, 18).render("Enter new SSID", True, lightbg, (255,255,255))
		label = labeltext.get_rect()
		label.center = labelblock.center
		surface.blit(labeltext, label)

	elif kind == "key":
		# Draw SSID and encryption type labels
		labelblock = pygame.draw.rect(surface, (255,255,255), (0,35,320,20))
		if len(ssid) >= 16:
			labeltext = pygame.font.SysFont(None, 18).render("Enter key for "+"%s..."%(ssid[:16]), True, lightbg, (255,255,255))
		else:
			labeltext = pygame.font.SysFont(None, 18).render("Enter key for "+ssid, True, lightbg, (255,255,255))
		label = labeltext.get_rect()
		label.center = labelblock.center
		surface.blit(labeltext, label)

	# Input area
	bg = pygame.draw.rect(surface, (255, 255, 255), (0, 55, 320, 45))
	text = "[ "
	text += passphrase
	text += " ]"
	pw = pygame.font.SysFont(None, size).render(text, True, (0, 0, 0), (255, 255, 255))
	pwtext = pw.get_rect()
	pwtext.center = bg.center
	surface.blit(pw, pwtext)
	pygame.display.update()

def selectkey(keyboard, kind, direction=""):
	def getcurrentkey(keyboard, pos):
		keys = getkeys(keyboard)
		for item in keys.iteritems():
			if item[1]['row'] == pos[1] and item[1]['column'] == pos[0]:
				currentkey = item[1]['key']
		return currentkey
	def highlightkey(keyboard, pos='[0,0]'):
		drawkeyboard(keyboard)
		pygame.display.update()

		left_margin = 32
		top_margin = 136

		if pos[0] > left_margin:
			x = left_margin + (16 * (pos[0]))
		else:
			x = left_margin + (16 * pos[0]) + (pos[0] * 4)
			

		if pos[1] > top_margin:
			y = top_margin + (16 * (pos[1]))
		else:
			y = top_margin + (16 * pos[1]) + (pos[1] * 4)

		list = [ \
					(x, y), \
					(x + 16, y), \
					(x + 16, y + 16), \
					(x, y + 16), \
					(x, y) \
				]
		lines = pygame.draw.lines(surface, (255,255,255), True, list, 1)
		pygame.display.update()

	global maxrows
	global maxcolumns
	global selected_key
	global passphrase

	if not selected_key:
		selected_key = [0,0]
		highlightkey(keyboard, selected_key)

	if direction == "swap":
		highlightkey(keyboard, selected_key)
	else:
		if direction == "up":
			if selected_key[1] <= 0:
				selected_key[1] = 0
			else:
				selected_key[1] -= 1
		elif direction == "down":
			if selected_key[1] >= maxrows - 1:
				selected_key[1] = maxrows - 1
			elif not getcurrentkey(keyboard, (selected_key[0], selected_key[1] + 1)):
				selected_key[1] = selected_key[1]
			else:
				selected_key[1] = selected_key[1] + 1
		elif direction == "left":
			if selected_key[0] <= 0:
				selected_key[0] = 0
			else:
				selected_key[0] = selected_key[0] - 1
		elif direction == "right":
			if selected_key[0] >= maxcolumns - 1:
				selected_key[0] = maxcolumns - 1
			elif not getcurrentkey(keyboard, (selected_key[0] + 1, selected_key[1])):
				selected_key[0] = selected_key[0]
			else:
				selected_key[0] = selected_key[0] + 1
		elif direction == "select":
			passphrase += getcurrentkey(keyboard, selected_key)
			if len(passphrase) > 20:
				drawlogobar()
				drawlogo()
				displayinputlabel(kind, 12)
			else:
				displayinputlabel(kind)
		elif direction == "space":
			passphrase += ' '
			if len(passphrase) > 20:
				drawlogobar()
				drawlogo()
				displayinputlabel(kind, 12)
			else:
				displayinputlabel(kind)
		elif direction == "delete":
			if len(passphrase) > 0:
				passphrase = passphrase[:-1]
				drawlogobar()
				drawlogo()
				if len(passphrase) > 20:
					displayinputlabel(kind, 12)
				else:
					displayinputlabel(kind)
	highlightkey(keyboard, selected_key)

class Menu:
	font_size = 16
	font = pygame.font.SysFont
	dest_surface = pygame.Surface
	canvas_color = darkbg

	elements = []

	def __init__(self):
		self.set_elements([])
		self.selected_item = 0
		self.origin = (0,0)
		self.menu_width = 0
		self.menu_height = 0
		self.selection_color = activeselbg
		self.text_color = activetext

	def move_menu(self, top, left):
		self.origin = (top, left)

	def set_colors(self, text, selection, background):
		self.text_color = text
		self.selection_color = selection
		
	def set_font(self, font):
		self.font = font

	def set_elements(self, elements):
		self.elements = elements

	def get_position(self):
		return self.selected_item

	def get_selected(self):
		return self.elements[self.selected_item]

	def init(self, elements, dest_surface):
		self.set_elements(elements)
		self.dest_surface = dest_surface
		
	def draw(self,move=0):
		if len(self.elements) == 0:
			return

		if move != 0:
			self.selected_item += move
			if self.selected_item < 0:
				self.selected_item = 0
			elif self.selected_item >= len(self.elements):
				self.selected_item = len(self.elements) - 1

		# Which items are to be shown?
		if self.selected_item <= 2: # We're at the top
			visible_elements = self.elements[0:5]
			selected_within_visible = self.selected_item
		elif self.selected_item >= len(self.elements) - 3: # We're at the bottom
			visible_elements = self.elements[-5:]
			selected_within_visible = self.selected_item - (len(self.elements) - len(visible_elements))
		else: # The list is larger than 5 elements, and we're in the middle
			visible_elements = self.elements[self.selected_item - 2:self.selected_item + 3]
			selected_within_visible = 2

		# What width does everything have?
		max_width = max([self.get_item_width(visible_element) for visible_element in visible_elements])
		# And now the height
		heights = [self.get_item_height(visible_element) for visible_element in visible_elements]
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
		pygame.draw.rect(menu_surface,self.selection_color,selection_rect)

		# Elements
		top = 0
		for i in xrange(len(visible_elements)):
			self.render_element(menu_surface, visible_elements[i], 0, top)
			top += heights[i]
		self.dest_surface.blit(menu_surface,self.origin)
		return self.selected_item

	def get_item_height(self, element):
		render = self.font.render(element, 1, self.text_color)
		spacing = 5
		return render.get_rect().height + spacing * 2

	def get_item_width(self, element):
		render = self.font.render(element, 1, self.text_color)
		spacing = 5
		return render.get_rect().width + spacing * 2

	def render_element(self, menu_surface, element, left, top):
		render = self.font.render(element, 1, self.text_color)
		spacing = 5
		menu_surface.blit(render, (left + spacing, top + spacing, render.get_rect().width, render.get_rect().height))

class NetworksMenu(Menu):
	def set_elements(self, elements):
		self.elements = elements
		self.font = pygame.font.Font('./data/Inconsolata.otf', 16)

	def get_item_width(self, element):
		if len(str(element[0])) > 16:
			the_ssid = "%s..."%(element[0][:16])
		else:
			the_ssid = element[0].ljust(19)

		render = self.font.render(the_ssid, 1, self.text_color)
		spacing = 15
		return render.get_rect().width + spacing * 2

	def get_item_height(self, element):
		render = self.font.render(element[0], 1, self.text_color)
		spacing = 5
		return (render.get_rect().height + spacing * 2) + 5

	def render_element(self, menu_surface, element, left, top):

		if len(str(element[0])) > 17:
			the_ssid = "%s..."%(element[0][:14])
		else:
			the_ssid = element[0].ljust(17)

		boldtext = pygame.font.Font('./data/Inconsolata.otf', self.font_size)
		subtext = pygame.font.Font('./data/Inconsolata.otf', 12)

		def qualityPercent(x):
			percent = (float(x.split("/")[0]) / float(x.split("/")[1])) * 100
			if percent > 100:
				percent = 100
			return int(percent)
		## Wifi signal icons
		percent = qualityPercent(element[1])

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

		## Encryption information
		enc_type = element[2]
		if enc_type == "none":
			enc_icon = "open.png"
			enc_type = "Open"
		elif enc_type == "wpa":
			enc_icon = "closed.png"
			enc_type = "WPA"
		elif enc_type == "wpa2":
			enc_icon = "closed.png"
			enc_type = "WPA2"
		elif enc_type == "wep":
			enc_icon = "closed.png"
			enc_type = "WEP"
		else:
			enc_icon = "unknown.png"
			enc_type = "(Unknown)"


		qual_img = pygame.image.load((os.path.join('data', signal_icon))).convert_alpha()
		enc_img = pygame.image.load((os.path.join('data', enc_icon))).convert_alpha()

		ssid = boldtext.render(the_ssid, 1, self.text_color)
		enc = subtext.render(enc_type, 1, lightgrey)
		strength = subtext.render(str(str(percent) + "%").rjust(4), 1, lightgrey)
		qual = subtext.render(element[1], 1, lightgrey)
		spacing = 2

		menu_surface.blit(ssid, (left + spacing, top, ssid.get_rect().width, ssid.get_rect().height))
		menu_surface.blit(enc, (left + enc_img.get_rect().width + 12, top + 18, enc.get_rect().width, enc.get_rect().height))
		menu_surface.blit(enc_img, pygame.rect.Rect(left + 8, (top + 24) - (enc_img.get_rect().height / 2), enc_img.get_rect().width, enc_img.get_rect().height))
		# menu_surface.blit(strength, (left + 137, top + 18, strength.get_rect().width, strength.get_rect().height))
		# menu_surface.blit(qual_img, pygame.rect.Rect(left + 140, top + 2, qual_img.get_rect().width, qual_img.get_rect().height))
		menu_surface.blit(qual_img, pygame.rect.Rect(left + 140, top + 8, qual_img.get_rect().width, qual_img.get_rect().height))
		pygame.display.flip()

	def draw(self,move=0):
		if len(self.elements) == 0:
			return

		if move != 0:
			self.selected_item += move
			if self.selected_item < 0:
				self.selected_item = 0
			elif self.selected_item >= len(self.elements):
				self.selected_item = len(self.elements) - 1

		# Which items are to be shown?
		if self.selected_item <= 2: # We're at the top
			visible_elements = self.elements[0:5]
			selected_within_visible = self.selected_item
		elif self.selected_item >= len(self.elements) - 3: # We're at the bottom
			visible_elements = self.elements[-5:]
			selected_within_visible = self.selected_item - (len(self.elements) - len(visible_elements))
		else: # The list is larger than 5 elements, and we're in the middle
			visible_elements = self.elements[self.selected_item - 2:self.selected_item + 3]
			selected_within_visible = 2

		# What width does everything have?
		max_width = max([self.get_item_width(visible_element) for visible_element in visible_elements])

		# And now the height
		heights = [self.get_item_height(visible_element) for visible_element in visible_elements]
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
		pygame.draw.rect(menu_surface,self.selection_color,selection_rect)

		# Elements
		top = 0
		for i in xrange(len(visible_elements)):
			self.render_element(menu_surface, visible_elements[i], 0, top)
			top += heights[i]
		self.dest_surface.blit(menu_surface,self.origin)
		return self.selected_item

def to_menu(new_menu):
	if new_menu == "main":
		menu.set_colors(activetext, activeselbg, darkbg)
		if wirelessmenu is not None:
			wirelessmenu.set_colors(inactivetext, inactiveselbg, darkbg)
	elif new_menu == "ssid" or new_menu == "saved":
		menu.set_colors(inactivetext, inactiveselbg, darkbg)
		wirelessmenu.set_colors(activetext, activeselbg, darkbg)
	return new_menu

wirelessmenu = None
menu = Menu()
menu.set_font(pygame.font.Font('./data/Inconsolata.otf', 16))
menu.move_menu(8, 41)

def mainmenu():
	elems = ['Scan for APs', "Manual Setup", "Saved Networks", "Quit"]
	if checkinterfacestatus(wlan):
		elems = ['Disconnect'] + elems
	menu.init(elems, surface)
 	menu.draw()

def create_wireless_menu():
	global wirelessmenu
	wirelessmenu = NetworksMenu()
	wirelessmenu.set_font(pygame.font.Font('./data/Inconsolata.otf', 14))
	wirelessmenu.move_menu(150,40)

def destroy_wireless_menu():
	global wirelessmenu
	wirelessmenu = None

def create_saved_networks_menu():
	global uniq
	uniq = getsavednets()
	wirelessitems = []
	l = []
	for item in sorted(uniq.iterkeys(), key=lambda x: uniq[x]['Network']['menu']):
		for network, detail in uniq.iteritems():
			if network == item:
				try:
					detail['Network']['Quality']
				except KeyError:
					detail['Network']['Quality'] = "0/1"
				try:
					detail['Network']['Encryption']
				except KeyError:
					detail['Network']['Encryption'] = ""

				ssidconfig = re.escape(detail['Network']['ESSID'])
				conf = netconfdir+ssidconfig+".conf"
				with open(conf) as f:
					for line in f:
						if "WLAN_ENCRYPTION" in line:
							detail['Network']['Encryption'] = str.strip(line[line.find('WLAN_ENCRYPTION="')\
								+len('WLAN_ENCRYPTION="'):line.find('"\n')+len('"\n')].rstrip('"\n'))
						if "WLAN_PASSPHRASE" in line:
							uniq[network]['Network']['Key'] = str.strip(line[line.find('WLAN_PASSPHRASE="')\
								+len('WLAN_PASSPHRASE="'):line.find('"\n')+len('"\n')].rstrip('"\n'))

				menuitem = [ detail['Network']['ESSID'], detail['Network']['Quality'], detail['Network']['Encryption']]
				l.append(menuitem)
	create_wireless_menu()
	wirelessmenu.init(l, surface)
	wirelessmenu.draw()
if __name__ == "__main__":
	# Persistent variables
	networks = {}
	uniqssids = {}
	active_menu = "main"

	try:
		createpaths()
	except:
		pass ## Can't create directories. Great for debugging on a pc.
	
	redraw()
	while True:
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
			# power up = K_KP0
			# power down = K_PAUSE

			if event.type == QUIT:
				pygame.display.quit()
				sys.exit()

			elif event.type == KEYDOWN:
				if event.key == K_PAUSE: # Power down
					pass
				elif event.key == K_TAB: # Left shoulder button
					pass
				elif event.key == K_BACKSPACE: # Right shoulder button
					pass
				elif event.key == K_KP0:	# Power up
					pass
				elif event.key == K_UP: # Arrow up the menu
					if active_menu == "main":
						menu.draw(-1)
					elif active_menu == "ssid" or active_menu == "saved":
						wirelessmenu.draw(-1)
				elif event.key == K_DOWN: # Arrow down the menu
					if active_menu == "main":
						menu.draw(1)
					elif active_menu == "ssid" or active_menu == "saved":
						wirelessmenu.draw(1)
				elif event.key == K_RIGHT:
					if wirelessmenu is not None and active_menu == "main":
						active_menu = to_menu("ssid")
						redraw()
				elif event.key == K_LALT or event.key == K_LEFT:
					if active_menu == "ssid" or active_menu == "saved":
						destroy_wireless_menu()
						active_menu = to_menu("main")
						del uniq
						redraw()
				elif event.key == K_SPACE:
					if active_menu == "saved":
						if len(str(wirelessmenu.get_selected()[0])) > 16:
							the_ssid = "%s..."%(wirelessmenu.get_selected()[0][:16])
						else:
							the_ssid = wirelessmenu.get_selected()[0]
						confirm = modal("Forget "+the_ssid+"?", query=True)
						if confirm:
							os.remove(netconfdir+re.escape(str(wirelessmenu.get_selected()[0]))+".conf")
						create_saved_networks_menu()
						redraw()
				elif event.key == K_LCTRL or event.key == K_RETURN:
					# Main menu
					if active_menu == "main":
						if menu.get_selected() == 'Disconnect':
							disconnect(wlan)
							redraw()
						elif menu.get_selected() == 'Scan for APs':
							try:
								getnetworks(wlan)
								uniq = listuniqssids()
							except:
								####### DEBUG #######
								uniqssid = {}
								uniqssids = {}
								uniqssid=uniqssids.setdefault('DEBUG', {'Network': {'ESSID': 'DEBUG', 'menu': 0}})
								uniqssid=uniqssids.setdefault('DEBUG network', {'Network': {'Encryption': 'wep', 'Quality': '0/100', 'ESSID': 'DEBUG network', 'menu': 1}})
								uniqssid=uniqssids.setdefault('Another Debug', {'Network': {'Encryption': 'wpa', 'Quality': '76/100', 'ESSID': 'Another Debug', 'menu': 2}})
								uniqssid=uniqssids.setdefault('DEBUG DEBUG DEBUG DEBUG', {'Network': {'Encryption': 'wpa2', 'Quality': '101/100', 'ESSID': 'DEBUG DEBUG DEBUG DEBUG', 'menu': 3}})
								uniqssid=uniqssids.setdefault('Hello DEBUG', {'Network': {'Encryption': 'wpa', 'Quality': '100/100', 'ESSID': 'Hello DEBUG', 'menu': 4}})
								uniqssid=uniqssids.setdefault('Oh My! Debug!', {'Network': {'Encryption': 'wpa2', 'Quality': '93/100', 'ESSID': 'Oh My! Debug!', 'menu': 5}})
								uniqssid=uniqssids.setdefault('More Debug?', {'Network': {'Encryption': 'wpa2', 'Quality': '2/100', 'ESSID': 'More Debug?', 'menu': 6}})
								uniqssid=uniqssids.setdefault('Yep! Debug!', {'Network': {'Encryption': 'wpa2', 'Quality': '56/100', 'ESSID': 'Yep! Debug!', 'menu': 7}})
								uniqssid=uniqssids.setdefault('The Quick Brown', {'Network': {'Encryption': 'wpa', 'Quality': '0/100', 'ESSID': 'The Quick Brown', 'menu': 8}})
								uniqssid=uniqssids.setdefault('Fox Jumps', {'Network': {'Encryption': 'wpa2', 'Quality': '80/100', 'ESSID': 'Fox Jumps', 'menu': 9}})
								uniqssid=uniqssids.setdefault('Over The', {'Network': {'Encryption': 'wep', 'Quality': '100/100', 'ESSID': 'Over The', 'menu': 10}})
								uniqssid=uniqssids.setdefault('Lazy Dog', {'Network': {'Encryption': 'wpa2', 'Quality': '97/100', 'ESSID': 'Lazy Dog', 'menu': 11}})
								uniqssid=uniqssids.setdefault('HaDAk', {'Network': {'Encryption': 'wpa2', 'Quality': '100/100', 'ESSID': 'HaDAk', 'menu': 12}})
								uniq = uniqssids
								####### DEBUG #######
							wirelessitems = []
							l = []
							for item in sorted(uniq.iterkeys(), key=lambda x: uniq[x]['Network']['menu']):
								for network, detail in uniq.iteritems():
									if network == item:
										try:
											detail['Network']['Quality']
										except KeyError:
											detail['Network']['Quality'] = "0/1"
										try:
											detail['Network']['Encryption']
										except KeyError:
											detail['Network']['Encryption'] = ""

										percent = (float(detail['Network']['Quality'].split("/")[0])\
													/ float(detail['Network']['Quality'].split("/")[1])) * 100
										if percent > 5:
											menuitem = [ detail['Network']['ESSID'], detail['Network']['Quality'], detail['Network']['Encryption']]
											l.append(menuitem)

							create_wireless_menu()
							wirelessmenu.init(l, surface)
							wirelessmenu.draw()

							active_menu = to_menu("ssid")
							redraw()

						elif menu.get_selected() == 'Manual Setup':
							ssid = ''
							encryption = ''
							securitykey = ''

							# Get SSID from the user
							ssid = getSSID()
							if ssid == '':
								pass
							else:
								ssidconfig = re.escape(ssid)

								drawEncryptionType()
								encryption = getEncryptionType()

								# Get key from the user
								if not encryption == 'None':
									if encryption == "WPA/WPA2":
										encryption = "wpa"
										displayinputlabel("key")
										drawkeyboard("qwertyNormal")
										securitykey = getinput("qwertyNormal", "key", ssid)
									elif encryption == "WEP":
										encryption = "wep"
										displayinputlabel("key")
										drawkeyboard("wep")
										securitykey = getinput("wep", "key", ssid)
									elif encryption == 'cancel':
										del encryption, ssid, ssidconfig, securitykey
										modal("Canceled.", timeout=True)
										redraw()
								else:
									encryption = "none"

								try:
									encryption
								except NameError:
									modal("Canceled.", timeout=True)
								else:
									conf = netconfdir+ssidconfig+".conf"
									writeconfig()
									connect(wlan)
									redraw()

						elif menu.get_selected() == 'Saved Networks':
							create_saved_networks_menu()
							active_menu = to_menu("saved")
							redraw()

						elif menu.get_selected() == 'Quit':
							pygame.display.quit()
							sys.exit()

					# SSID menu		
					elif active_menu == "ssid":
						ssid = ""

						for network, detail in uniq.iteritems():
							position = str(wirelessmenu.get_position())
							if str(detail['Network']['menu']) == position:
								ssid = network
								ssidconfig = re.escape(ssid)
								conf = netconfdir+ssidconfig+".conf"
								if not os.path.exists(conf):
									if detail['Network']['Encryption'] == "none":
										passphrase = "none"
										encryption = "none"
									elif detail['Network']['Encryption'] == "wep":
										displayinputlabel("key")
										drawkeyboard("wep")
										encryption = "wep"
										getinput("wep", "key", ssid)
									else:
										displayinputlabel("key")
										drawkeyboard("qwertyNormal")
										encryption = "wpa"
										getinput("qwertyNormal", "key", ssid)
									writeconfig()
								connect(wlan)
								redraw()
								break

					# Saved Networks menu
					elif active_menu == "saved":
						ssid = ''
						for network, detail in uniq.iteritems():
							position = str(wirelessmenu.get_position()+1)
							if str(detail['Network']['menu']) == position:
								encryption = detail['Network']['Encryption']
								ssidconfig = re.escape(str(detail['Network']['ESSID']))
								shutil.copy2(netconfdir+ssidconfig+".conf", sysconfdir+"config-"+wlan+".conf")
								passphrase = detail['Network']['Key']
								connect(wlan)
								redraw()
								break

				elif event.key == K_ESCAPE:
					if active_menu == "ssid": # Allow us to edit the existing key
						ssid = ""

						for network, detail in uniq.iteritems():
							position = str(wirelessmenu.get_position())
							if str(detail['Network']['menu']) == position:
								ssid = network
								ssidconfig = re.escape(ssid)
								if detail['Network']['Encryption'] == "none":
									pass
								elif detail['Network']['Encryption'] == "wep":
									displayinputlabel("key")
									drawkeyboard("wep")
									getinput("wep", "key", ssid)
								else:
									displayinputlabel("key")
									drawkeyboard("qwertyNormal")
									getinput("qwertyNormal", "key", ssid)

					if active_menu == "saved": # Allow us to edit the existing key
						ssid = ''

						for network, detail in uniq.iteritems():
							position = str(wirelessmenu.get_position()+1)
							if str(detail['Network']['menu']) == position:
								ssid = network
								ssidconfig = re.escape(ssid)
								passphrase = uniq[network]['Network']['Key']
								if uniq[network]['Network']['Encryption'] == "none":
									pass
								elif uniq[network]['Network']['Encryption'] == "wep":
									displayinputlabel("key")
									drawkeyboard("wep")
									getinput("wep", "key", ssid)
								else:
									displayinputlabel("key")
									drawkeyboard("qwertyNormal")
									getinput("qwertyNormal", "key", ssid)


		pygame.display.update()
