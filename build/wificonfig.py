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
* Add manual network configuration option
* Rewrite menus to give better scrolling options, and not have to do logic by menu position instead of content
* Allow viewing/deleting saved networks
* Show signal strength of scanned SSIDs

Known bugs:

* Scrolling around the ssid menu will crash it if you try to go past the end or beginning
* Scrolling down a page of SSIDs in the menu, then going back up, and back down causes the cursor to jump to the top
'''


import subprocess as SU
import sys, time, os, shutil, re
import pygame
from pygame.locals import *

# What is our wireless interface?
wlan = "wlan0"

# How many times do you want to try to
# connect to a network before we give up?
timeout = 3

darkbg = (41, 41, 41)
lightbg = (84, 84, 84)
activeselbg = (153, 0, 0)
inactiveselbg = (84, 84, 84)
activetext = (255, 255, 255)
inactivetext = (128, 128, 128)

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
go = ''
active_menu = ''

## Initialize the dispaly, for pygame
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
def ifdown():
	modal("Disabling WiFi...","false")
	command = ['ifdown', wlan]
	with open(os.devnull, "w") as fnull:
		SU.Popen(command, stderr = fnull)
	command = ['rfkill', 'block', 'wlan']
	with open(os.devnull, "w") as fnull:
		SU.Popen(command, stderr = fnull)
	try:
		os.remove(sysconfdir+"config-"+wlan+".conf")
	except:
		pass
	time.sleep(1)
def enablewifi():
	check = checkinterfacestatus()
	if not check:
		modal("Enabling WiFi...","false")
		command = ['rfkill', 'unblock', 'wlan']
		with open(os.devnull, "w") as fnull:
			SU.Popen(command, stderr = fnull)

		command = ['ifconfig']
		output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()
		drawinterfacestatus()
		pygame.display.update()
		good = ''
		while not good:
			for line in output:
				if line.strip().startswith("wlan"):
					good = "ok"
				else:
					command = ['ifconfig', wlan, 'up']
					with open(os.devnull, "w") as fnull:
						SU.Popen(command, stdout = fnull, stderr = fnull)
					command = ['ifconfig']
					output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()
def ifup():
	oldssid = ''
	if getcurrentssid():
		oldssid = getcurrentssid()
	counter = 0
	check = checkinterfacestatus()
	if not check:
		enablewifi()
	else:
		modal("Connecting...","false")
		check = ''
		while not check and counter < timeout:
			if counter > 0:
				modal('Connection failed. Retrying...'+str(counter),"false")
			command = ['ifup', wlan]
			with open(os.devnull, "w") as fnull:
				output = SU.Popen(command, stdout=SU.PIPE, stderr = fnull).stdout.readlines()
			counter += 1
			drawstatusbar()
			drawinterfacestatus()
			pygame.display.update()
			if counter >= timeout:
				modal('Connection failed!',wait="true")
			else:
				wlanstatus = ""
				currentssid = getcurrentssid()
				if not checkinterfacestatus() == "offline":
					if not currentssid == "unassociated":
						modal("Connected!","false","true")
			check = checkinterfacestatus()
def getwlanip():
	ip = ""
	command = ['ifconfig']
	with open(os.devnull, "w") as fnull:
		output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()

	for line in output:
		if line.strip().startswith("inet addr"):
			ip = str.strip(line[line.find('inet addr')+len('inet addr"'):line.find('Bcast')+len('Bcast')].rstrip('Bcast'))
			if ip == "10.1.1.2" or ip == "127.0.0.1":
				ip = ''
	return ip
def checkinterfacestatus():
	interface = "" # set default assumption of interface status
	ip = ""
	command = ['ifconfig']
	with open(os.devnull, "w") as fnull:
		output = SU.Popen(command, stdout=SU.PIPE, stderr = fnull).stdout.readlines()

	for line in output:
		if line.strip().startswith(wlan):
			ip = getwlanip()
			if ip:
				interface = ip
			else:
				currentssid = getcurrentssid()
				if currentssid == "unassociated":
					interface = "disconnected"
			
	return interface
def getnetworks(): # Run iwlist to get a list of networks in range
	enablewifi()
	modal("Scanning...","false")
	command = ['iwlist', wlan, 'scan']
	with open(os.devnull, "w") as fnull:
		output = SU.Popen(command, stdout=SU.PIPE, stderr = fnull).stdout.readlines()
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
def getwlanstatus():
	global wlan
	wlanstatus = ''
	command = ['ifconfig']
	with open(os.devnull, "w") as fnull:
		output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()

	for line in output:
		if line.strip().startswith(wlan):
			wlanstatus = "ok"
	return wlanstatus

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
		encryption = "wep"

	elif encryption.startswith("IE: WPA"):
		encryption = "wpa"

	elif encryption.startswith("IE: IEEE 802.11i/WPA2"):
		encryption = "wpa2"

	else:
		encryption = "Encrypted (unknown)"

	return encryption

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
	wlanstatus = getwlanstatus()
	if not wlanstatus: 
		wlanstatus = wlan+" is off."
	else:
		currentssid = getcurrentssid()
		if currentssid == "unassociated":
			wlanstatus = wlan+" is disconnected."
		elif not currentssid == "unassociated":
			wlanstatus = currentssid
	

	wlantext = pygame.font.SysFont(None, 16).render(wlanstatus, True, (255, 255, 255), lightbg)
	wlan_text = wlantext.get_rect()
	wlan_text.topleft = (4, 227)
	surface.blit(wlantext, wlan_text)

	if not checkinterfacestatus() == "not connected" and not checkinterfacestatus() == "disconnected":
		text = pygame.font.SysFont(None, 16).render(checkinterfacestatus(), True, (153, 0, 0), lightbg)
		interfacestatus_text = text.get_rect()
		interfacestatus_text.topright = (315, 227)
		surface.blit(text, interfacestatus_text)
def getcurrentssid(): # What network are we connected to?
	ssid = ''
	command = ['iwconfig', wlan]
	with open(os.devnull, "w") as fnull:
		output = SU.Popen(command, stdout=SU.PIPE, stderr = fnull).stdout.readlines()

	for line in output:
		if line.strip().startswith(wlan):
			ssid = str.strip(line[line.find('ESSID')+len('ESSID:"'):line.find('Nickname:')+len('Nickname:')].rstrip(' Nickname:').rstrip('"'))

	return ssid
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

	drawstatusbar()
	drawinterfacestatus()
	pygame.display.update()
def modal(text,wait="true",timeout="false"): # Draw a modal
	dialog = pygame.draw.rect(surface, lightbg, (64,88,192,72))
	pygame.draw.rect(surface, (255,255,255), (62,86,194,74), 2)

	text = pygame.font.SysFont(None, 16).render(text, True, (255, 255, 255), lightbg)
	modal_text = text.get_rect()
	modal_text.center = dialog.center

	surface.blit(text, modal_text)
	pygame.display.update()

	if not wait == "true" and timeout == "true":
		time.sleep(2.5)
		redraw()
	elif wait == "true":
		abutton = hint("a", "Continue", 205, 145, lightbg)
		pygame.display.update()

	while wait == "true":
		for event in pygame.event.get():
			if event.type == KEYDOWN:
				if event.key == K_LCTRL:
					redraw()
					wait = "false"

## Connect to a network
def writeconfig(mode="a"): # Write wireless configuration to disk
	global passphrase
	if passphrase:
		if passphrase == "none":
			passphrase = ""
		conf = netconfdir+ssidconfig+".conf"
		f = open(conf, mode)
		f.write('WLAN_ESSID="'+ssid+'"\n')
		f.write('WLAN_ENCRYPTION="'+uniq[ssid]['Network']['Encryption']+'"\n')
		f.write('WLAN_PASSPHRASE="'+passphrase+'"\n')
		f.write('WLAN_DHCP_RETRIES=20\n')
		f.close()
def connect(): # Connect to a network
	global go
	if go == "true":
		oldconf = netconfdir+ssidconfig+".conf"
		newconf = sysconfdir +"config-wlan0.conf"
		os.environ['CONFIG_FILE'] = netconfdir+ssidconfig+".conf"
		shutil.copy2(oldconf, newconf)
		ifup()

## Keyboard
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
	
	if board == "qwertyNormal":
		k = qwertyNormal()
	elif board == "qwertyShift":
		k = qwertyShift()
	elif board == "wep":
		k = wep()
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
def drawkeyboard(board, ssid):

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
	else:
		hint("y", "Full KB", 200, 227, lightbg)
		#uniq[ssid]['Network']['Encryption'] = "wpa2" ## Will need to put this somewhere to fix the wep bug
	hint("b", "Space", 240, 227, lightbg)
	hint("a", "Enter", 285, 227, lightbg)

	# Draw the keys

	k = getkeys(board)
	z = key()

	for x, y in k.iteritems():
		if y['key']:
			z.init(y['key'],y['row'],y['column'])

	pygame.display.update()
	return keyboard
def getinput(board, ssid):
	selectkey(board, ssid)
	security = softkeyinput(board, ssid)
	return security
def softkeyinput(keyboard, ssid):
	global passphrase
	global go
	wait = "true"
	while wait == "true":
		for event in pygame.event.get():

			if event.type == KEYDOWN:
				if event.key == K_RETURN:		# finish input
					selectkey(keyboard, "enter")
					wait = "false"

				if event.key == K_UP:		# Move cursor up
					selectkey(keyboard, ssid, "up")
				if event.key == K_DOWN:		# Move cursor down
					selectkey(keyboard, ssid, "down")
				if event.key == K_LEFT:		# Move cursor left
					selectkey(keyboard, ssid, "left")
				if event.key == K_RIGHT:	# Move cursor right
					selectkey(keyboard, ssid, "right")
				if event.key == K_LCTRL:	# A button
					selectkey(keyboard, ssid, "select")
				if event.key == K_LALT:		# B button
					selectkey(keyboard, ssid, "space")
				if event.key == K_SPACE:	# Y button (swap keyboards)
					if not uniq[ssid]['Network']['Encryption'] == "wpa2" \
						or not uniq[ssid]['Network']['Encryption'] == "wpa":
						uniq[ssid]['Network']['Encryption'] = "wpa2"
						# TESTING DEBUG
						# This may work, or it may not. Will need to revisit it.
						# TODO

					if keyboard == "qwertyNormal":
						keyboard = "qwertyShift"
						drawkeyboard(keyboard, ssid)
						selectkey(keyboard, ssid, "swap")
					elif keyboard == "qwertyShift":
						keyboard = "qwertyNormal"
						drawkeyboard(keyboard, ssid)
						selectkey(keyboard, ssid, "swap")
					else:
						keyboard = "qwertyNormal"
						drawkeyboard(keyboard, ssid)
						selectkey(keyboard, ssid, "swap")	
				if event.key == K_LSHIFT:	# X button
					selectkey(keyboard, ssid, "delete")
				if event.key == K_ESCAPE:	# Select key
					passphrase = ''
					wait = "false"
				if event.key == K_RETURN:	# Start key
					redraw()
					writeconfig("w")
					go = "true"
					modal("Connecting...","false")
					connect()
					drawinterfacestatus()
					wait = "false"
					passphrase = ''
	redraw()
	return go
def displaypassphrase(passphrase, size=24): # Display passphrase on screen

	# Draw SSID and encryption type labels
	labelblock = pygame.draw.rect(surface, (255,255,255), (0,35,320,20))
	labeltext = pygame.font.SysFont(None, 18).render("Enter key for "+ssid, True, lightbg, (255,255,255))
	label = labeltext.get_rect()
	label.center = labelblock.center
	surface.blit(labeltext, label)

	# Passphrase area
	bg = pygame.draw.rect(surface, (255, 255, 255), (0, 55, 320, 45))
	text = "[ "
	text += passphrase
	text += " ]"
	pw = pygame.font.SysFont(None, size).render(text, True, (0, 0, 0), (255, 255, 255))
	pwtext = pw.get_rect()
	pwtext.center = bg.center
	surface.blit(pw, pwtext)
	pygame.display.update()
def selectkey(keyboard, ssid, direction="none"):
	def getcurrentkey(keyboard, pos):
		keys = getkeys(keyboard)
		for item in keys.iteritems():
			if item[1]['row'] == pos[1] and item[1]['column'] == pos[0]:
				currentkey = item[1]['key']
		return currentkey
	def highlightkey(keyboard, ssid, pos='[0,0]'):
		drawkeyboard(keyboard, ssid)
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
		highlightkey(keyboard, ssid, selected_key)

	if direction == "swap":
		highlightkey(keyboard, ssid, selected_key)
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
				displaypassphrase(passphrase, 12)
			else:
				displaypassphrase(passphrase)
		elif direction == "space":
			passphrase += ' '
			if len(passphrase) > 20:
				drawlogobar()
				drawlogo()
				displaypassphrase(passphrase, 12)
			else:
				displaypassphrase(passphrase)
		elif direction == "delete":
			if len(passphrase) > 0:
				passphrase = passphrase[:-1]
				drawlogobar()
				drawlogo()
				if len(passphrase) > 20:
					displaypassphrase(passphrase, 12)
				else:
					displaypassphrase(passphrase)
	highlightkey(keyboard, ssid, selected_key)

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
def to_menu(new_menu):
	if new_menu == "main":
		menu.set_colors(activetext, activeselbg, darkbg)
		if wirelessmenu is not None:
			wirelessmenu.set_colors(inactivetext, inactiveselbg, darkbg)
	elif new_menu == "ssid":
		menu.set_colors(inactivetext, inactiveselbg, darkbg)
		wirelessmenu.set_colors(activetext, activeselbg, darkbg)
	return new_menu

wirelessmenu = None
menu = Menu()
menu.set_font(pygame.font.Font('./data/Inconsolata.otf', 16))
menu.move_menu(16, 96)
def mainmenu():
	status = getwlanstatus()
	if not status == "ok":
		menu.init(['Scan for APs', "Manual setup", "Turn WiFi on", "Quit"], surface)
	else:
		menu.init(['Scan for APs', "Manual setup", "Turn WiFi off", "Quit"], surface)
	menu.draw()
def create_wireless_menu():
	global wirelessmenu
	wirelessmenu = Menu()
	wirelessmenu.set_font(pygame.font.Font('./data/Inconsolata.otf', 14))
	wirelessmenu.move_menu(150,40)
def destroy_wireless_menu():
	global wirelessmenu
	wirelessmenu = None

if __name__ == "__main__":
	# Persistent variables
	networks = {}
	uniqssids = {}
	currentssid = ""
	active_menu = "main"
	createpaths()	# DEBUG
	redraw()
	while 1:
		time.sleep(0.016)
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
					elif active_menu == "ssid":
						wirelessmenu.draw(-1)
				elif event.key == K_DOWN: # Arrow down the menu
					if active_menu == "main":
						menu.draw(1)
					elif active_menu == "ssid":
						wirelessmenu.draw(1)
				elif event.key == K_RIGHT:
					if wirelessmenu is not None and active_menu == "main":
						active_menu = to_menu("ssid")
						redraw()
				elif event.key == K_LALT or event.key == K_LEFT:
					if active_menu == "ssid":
						destroy_wireless_menu()
						active_menu = to_menu("main")
						redraw()
				elif event.key == K_LCTRL or event.key == K_RETURN:
					# Main menu
					if active_menu == "main":
						if menu.get_position() == 0: # Scan menu
							####### DEBUG #######
							# uniqssid = {}
							# uniqssids = {}
							# uniqssid=uniqssids.setdefault('apple', {'Network': {'Encryption': 'wpa2', 'Quality': '100/100', 'ESSID': 'apple', 'menu': 0}})
							# uniqssid=uniqssids.setdefault('MOTOROLA-92FCB', {'Network': {'Encryption': 'wpa2', 'ESSID': 'MOTOROLA-92FCB', 'menu': 1}})
							# uniqssid=uniqssids.setdefault('ATT264', {'Network': {'Encryption': 'wpa2', 'Quality': '76/100', 'ESSID': 'ATT264', 'menu': 2}})
							# uniqssid=uniqssids.setdefault('BLAH BLAH BLAHBLAH BLAH BLAHBLAH BLAH BLAH', {'Network': {'Encryption': 'wpa2', 'Quality': '101/100', 'ESSID': 'BLAH BLAH BLAHBLAH BLAH BLAHBLAH BLAH BLAH', 'menu': 3}})
							# uniqssid=uniqssids.setdefault('PS3-9434763', {'Network': {'Encryption': 'wpa', 'Quality': '100/100', 'ESSID': 'PS3-9434763', 'menu': 4}})
							# uniqssid=uniqssids.setdefault('BASocialWorkers', {'Network': {'Encryption': 'wpa2', 'Quality': '93/100', 'ESSID': 'BASocialWorkers', 'menu': 5}})
							# uniqssid=uniqssids.setdefault('HOME-A128', {'Network': {'Encryption': 'wpa2', 'Quality': '2/100', 'ESSID': 'HOME-A128', 'menu': 6}})
							# uniqssid=uniqssids.setdefault('GoBlue', {'Network': {'Encryption': 'wpa2', 'Quality': '56/100', 'ESSID': 'GoBlue', 'menu': 7}})
							# uniqssid=uniqssids.setdefault('yangji', {'Network': {'Encryption': 'wpa', 'ESSID': 'yangji', 'menu': 8}})
							# uniqssid=uniqssids.setdefault('U+zone', {'Network': {'Encryption': 'wpa2', 'Quality': '80/100', 'ESSID': 'U+zone', 'menu': 9}})
							# uniqssid=uniqssids.setdefault('U+Net7a77', {'Network': {'Encryption': 'wep', 'Quality': '100/100', 'ESSID': 'U+Net7a77', 'menu': 10}})
							# uniqssid=uniqssids.setdefault('Pil77Jung84', {'Network': {'Encryption': 'wpa2', 'Quality': '97/100', 'ESSID': 'Pil77Jung84', 'menu': 11}})
							# uniqssid=uniqssids.setdefault('HaDAk', {'Network': {'Encryption': 'wpa2', 'Quality': '100/100', 'ESSID': 'HaDAk', 'menu': 12}})
							# uniq = uniqssids
							####### DEBUG #######	
							getnetworks()				## TEMPORARILY DISABLE FOR TESTING WITHOUT LIVE SCANNING
							uniq = listuniqssids()		## TEMPORARILY DISABLE FOR TESTING WITHOUT LIVE SCANNING
							wirelessitems = []
							l = []
							for item in sorted(uniq.iterkeys(), key=lambda x: uniq[x]['Network']['menu']):
								for network, detail in uniq.iteritems():
									if network == item:
										s = str(detail['Network']['ESSID'])
										if len(str(detail['Network']['ESSID'])) > 16:
											menuitem = "%s..."%(s[:16])
										else:
											menuitem = s.ljust(19)
										l.append(menuitem)

							create_wireless_menu()
							wirelessmenu.init(l, surface)
							wirelessmenu.draw()

							active_menu = to_menu("ssid")
							redraw()

						elif menu.get_position() == 1: # Manual setup
							modal("Manual setup")

						elif menu.get_position() == 2: # Toggle wifi
							status = getwlanstatus()
							if not status == "ok":
								ifup()
								redraw()
								status = ''
							else:
								ifdown()
								redraw()
								status = ''

						elif menu.get_position() == 3: # Quit menu
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
										writeconfig()
										go = "true"
										connect()
										redraw()
									elif detail['Network']['Encryption'] == "wep":
										displaypassphrase(passphrase)
										drawkeyboard("wep", ssid)
										getinput("wep", ssid)
									else:
										displaypassphrase(passphrase)
										drawkeyboard("qwertyNormal", ssid)
										getinput("qwertyNormal", ssid)
								else:
									go = "true"
									connect()
									redraw()							
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
									displaypassphrase(passphrase)
									drawkeyboard("wep", ssid)
									getinput("wep", ssid)
								else:
									displaypassphrase(passphrase)
									drawkeyboard("qwertyNormal", ssid)
									getinput("qwertyNormal", ssid)

		pygame.display.update()
