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

## TEMPORARY ##
passphrase = ''

# What is our wireless interface?
wlan = "wlan0"

# How many times do you want to try to
# connect to a network before we give up?
timeout = 3

## That's it for options. Everything else below shouldn't be edited.
confdir = "/boot/local/home/.gcwconnect/"
sysconfdir = "/usr/local/etc/network/"
surface = pygame.display.set_mode((320,240))
keyboard = ''
selected_key = ''
maxrows = ''
maxcolumns = ''

def createpaths(): # Create paths, if necessary
	if not os.path.exists(confdir):
		os.makedirs(confdir)
	if not os.path.exists(sysconfdir):
		os.makedirs(sysconfdir)

# Initialize the dispaly, for pygame
if not pygame.display.get_init():
	pygame.display.init()

if not pygame.font.get_init():
	pygame.font.init()

## Interface management
def ifdown():
	command = ['ifdown', wlan]
	output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()
def ifup():
	counter = 0

	while checkinterfacestatus() == '' and counter < timeout:
		if counter > 0:
			modal('Connection failed. Retrying...'+str(counter),"false")
		command = ['ifup', wlan]
		output = SU.Popen(command, stdout=SU.PIPE).stdout.readlines()
		counter += 1

		if counter >= timeout:
			modal('Connection failed!',wait="true")

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
	menuposition = 0
	uniqssid = {}
	uniqssids = {}

	for network, detail in networks.iteritems():
			if detail['ESSID'] not in uniqssids and detail['ESSID']:
				uniqssid = uniqssids.setdefault(detail['ESSID'], {})
				uniqssid["Network"] = detail
				uniqssid["Network"]["menu"] = menuposition
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
	return quality
def parseencryption(encryption):
	encryption = str.strip(encryption)

 	if encryption.startswith('Encryption key:off'):
	 	encryption = "none"

	elif encryption.startswith('Encryption key:on'):
		#encryption = "Encrypted (unknown)"
		encryption = "wpa2"
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

	gcw_font = pygame.font.Font('./data/gcwzero.ttf', 24)

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
	dialog = pygame.draw.rect(surface, (84,84,84), (64,88,192,72))
	pygame.draw.rect(surface, (255,255,255), (62,86,194,74), 2)

	text = pygame.font.SysFont(None, 16).render(text, True, (255, 255, 255), (84,84,84))
	modal_text = text.get_rect()
	modal_text.center = dialog.center

	def drawcontinue():
		abutton = pygame.draw.circle(surface, (0, 0, 128), (208,151), 5) # (x, y)
		a = pygame.font.SysFont(None, 10).render("A", True, (255, 255, 255), (0,0,128))
		atext = a.get_rect()
		atext.center = abutton.center
		surface.blit(a, atext)

		labelblock = pygame.draw.rect(surface, (84,84,84), (218,144,32,14))
		labeltext = pygame.font.SysFont(None, 12).render("Continue", True, (255, 255, 255), (84,84,84))
		label = labeltext.get_rect()
		label.center = labelblock.center
		surface.blit(labeltext, label)
		pygame.display.update()

	surface.blit(text, modal_text)
	pygame.display.update()

	if not wait == "true" and timeout == "true":
		time.sleep(2.5)
		redraw()

	while wait == "true":
		drawcontinue()
		for event in pygame.event.get():
			if event.type == KEYDOWN:
				if event.key == K_LCTRL:
					redraw()
					wait = "false"

def writeconfig(): # Write wireless configuration to disk
	f = open(ssidconfig, "a")
	f.write('WLAN_ESSID="'+ssid+'"\n')
	f.write('WLAN_MODE="managed"\n')
	f.write('WLAN_ENCRYPTION="'+uniq[ssid]['Network']['Encryption']+'"\n')
	f.write('WLAN_PASSPHRASE="'+passphrase+'"\n') # TODO: on-screen keyboard for manual key entry
	f.write('WLAN_DRIVER="wext"\n')
	f.write('WLAN_DHCP_RETRIES=20\n')
	f.close()
def connect(): # Connect to a network
	oldconf = ssidconfig
	newconf = sysconfdir +"config-wlan0.conf"
	shutil.copy2(ssidconfig, newconf)
	ifdown()
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
		self.selection_color = (153,0,0)
		self.text_color =  (255,255,255)
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
		top = ''
		left = ''

		if self.row == 0:
			top = 136
		elif self.row == 1:
			top = 156
		elif self.row == 2:
			top = 176
		elif self.row == 3:
			top = 196
		elif self.row == 4:
			top = 216

		if self.column == 0:
			left = 32
		elif self.column == 1:
			left = 52
		elif self.column == 2:
			left = 72
		elif self.column == 3:
			left = 92
		elif self.column == 4:
			left = 112
		elif self.column == 5:
			left = 132
		elif self.column == 6:
			left = 152
		elif self.column == 7:
			left = 172
		elif self.column == 8:
			left = 192
		elif self.column == 9:
			left = 212
		elif self.column == 10:
			left = 232
		elif self.column == 11:
			left = 252
		elif self.column == 12:
			left = 272

		if len(self.key) > 1:
			key_width = 36
		keybox = pygame.draw.rect(surface, (50,50,50), (left,top,key_width,key_height))
		text = pygame.font.SysFont(None, 16).render(self.key, True, (255, 255, 255), (50,50,50))
		label = text.get_rect()
		label.center = keybox.center
		surface.blit(text, label)
def drawkeyboard(board):
	yellow = (128, 128, 0)
	blue = (0, 0, 128)
	red = (128, 0, 0)
	green = (0, 128, 0)
	black = (0, 0, 0)

	# Draw keyboard background 
	pygame.draw.rect(surface, (84,84,84), (0,100,320,140))

	# Draw the delete icon
	xbutton = pygame.draw.circle(surface, red, (160,230), 5) # (x, y)
	x = pygame.font.SysFont(None, 10).render("X", True, (255, 255, 255), red)
	xtext = x.get_rect()
	xtext.center = xbutton.center
	surface.blit(x, xtext)

	labelblock = pygame.draw.rect(surface, (84,84,84), (170,223,20,14))
	labeltext = pygame.font.SysFont(None, 12).render("Delete", True, (255, 255, 255), (84,84,84))
	label = labeltext.get_rect()
	label.center = labelblock.center
	surface.blit(labeltext, label)

	# Draw the shift icon
	ybutton = pygame.draw.circle(surface, yellow, (205,230), 5) # (x, y)
	y = pygame.font.SysFont(None, 10).render("Y", True, (255, 255, 255), yellow)
	ytext = y.get_rect()
	ytext.center = ybutton.center
	surface.blit(y, ytext)

	labelblock = pygame.draw.rect(surface, (84,84,84), (210,223,25,14))
	labeltext = pygame.font.SysFont(None, 12).render("Shift", True, (255, 255, 255), (84,84,84))
	label = labeltext.get_rect()
	label.center = labelblock.center
	surface.blit(labeltext, label)

	# Draw the enter icon(s)
	labelblock = pygame.draw.rect(surface, (84,84,84), (248,223,35,14))
	labeltext = pygame.font.SysFont(None, 12).render("/       Enter", True, (255, 255, 255), (84,84,84))
	label = labeltext.get_rect()
	label.center = labelblock.center
	surface.blit(labeltext, label)

	abutton = pygame.draw.circle(surface, green, (242,230), 5) # (x, y)
	a = pygame.font.SysFont(None, 10).render("A", True, (255, 255, 255), green)
	atext = a.get_rect()
	atext.center = abutton.center
	surface.blit(a, atext)

	bbutton = pygame.draw.circle(surface, blue, (255,230), 5) # (x, y)
	b = pygame.font.SysFont(None, 10).render("B", True, (255, 255, 255), blue)
	btext = b.get_rect()
	btext.center = bbutton.center
	surface.blit(b, btext)

	# Draw the finish icon
	pygame.draw.rect(surface, black, (32, 225, 35, 5))
	pygame.draw.circle(surface, black, (37, 230), 5)
	pygame.draw.circle(surface, black, (62, 230), 5)

	startbutton = pygame.draw.rect(surface, black, (37, 225, 25, 10))
	start = pygame.font.SysFont(None, 10).render("START", True, (255, 255, 255), black)
	starttext = start.get_rect()
	starttext.center = startbutton.center
	surface.blit(start, starttext)

	labelblock = pygame.draw.rect(surface, (84,84,84), (70,223,25,14))
	labeltext = pygame.font.SysFont(None, 12).render("Finish", True, (255, 255, 255), (84,84,84))
	label = labeltext.get_rect()
	label.center = labelblock.center
	surface.blit(labeltext, label)



	
	# Draw the keys
	k = getkeys(board)
	z = key()

	for x, y in k.iteritems():
		if y['key']:
			z.init(y['key'],y['row'],y['column'])

	pygame.display.update()
	return keyboard
def input(board):
	selectkey(board)
	security = softkeyinput(board)
	return security
def softkeyinput(keyboard):
	security = ''
	wait = "true"
	while wait == "true":
		for event in pygame.event.get():

			if event.type == KEYDOWN:
				if event.key == K_RETURN:		# finish input
					selectkey(keyboard, "enter")
					wait = "false"

				if event.key == K_UP:		# Move cursor up
					selectkey(keyboard, "up")
				if event.key == K_DOWN:		# Move cursor down
					selectkey(keyboard, "down")
				if event.key == K_LEFT:		# Move cursor left
					selectkey(keyboard, "left")
				if event.key == K_RIGHT:	# Move cursor right
					selectkey(keyboard, "right")
				if event.key == K_LCTRL:	# A button
					selectkey(keyboard, "select")
				if event.key == K_LALT:		# B button
					selectkey(keyboard, "select")
				if event.key == K_SPACE:	# shift
					if keyboard == "qwertyNormal":
						keyboard = "qwertyShift"
					elif keyboard == "qwertyShift":
						keyboard = "qwertyNormal"
					drawkeyboard(keyboard)
					selectkey(keyboard, "swap")
				if event.key == K_TAB:		# move cursor left
					pass
				if event.key == K_BACKSPACE:	# move cursor right
					pass
	redraw()
	return security
def selectkey(keyboard, direction="none"):
	def getcurrentkey(keyboard, pos):
		keys = getkeys(keyboard)
		for item in keys.iteritems():
			if item[1]['row'] == pos[1] and item[1]['column'] == pos[0]:
				currentkey = item[1]['key']
		return currentkey
	def highlightkey(keyboard, pos):
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
			highlightkey(keyboard, selected_key)
		elif direction == "down":
			if selected_key[1] >= maxrows - 1:
				selected_key[1] = maxrows - 1
			else:
				selected_key[1] = selected_key[1] + 1
			highlightkey(keyboard, selected_key)
		elif direction == "left":
			if selected_key[0] <= 0:
				selected_key[0] = 0
			else:
				selected_key[0] = selected_key[0] - 1
			highlightkey(keyboard, selected_key)
		elif direction == "right":
			if selected_key[0] >= maxcolumns - 1:
				selected_key[0] = maxcolumns - 1
			else:
				selected_key[0] = selected_key[0] + 1
			highlightkey(keyboard, selected_key)
		elif direction == "select":
			passphrase += getcurrentkey(keyboard, selected_key)
		elif direction == "enter":
			print passphrase

	#draw_selected_key(keyboard, selected_key)
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
	# Persistent variables
	networks = {}
	uniqssids = {}
	currentssid = ""
	createpaths()
	surface.fill((41,41,41))
	pygame.mouse.set_visible(False)
	pygame.key.set_repeat(199,69) #(delay,interval)
	redraw()
	active_menu = "main"

	# Define which keyboard to draw, then output the key entered as a variable
	keyboard = "qwertyNormal"
	drawkeyboard(keyboard)
	passphrase = input(keyboard)

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

							wirelessitems = []
							wirelessmenu.set_fontsize(14)

							for key in sorted(uniq.iterkeys(), key=lambda x: uniq[x]['Network']['menu']):
								wirelessitems.append(key)

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
						ssid = ""
						netconfdir = confdir+"networks/"
						if not os.path.exists(netconfdir):
							os.makedirs(netconfdir)

						for network, detail in uniq.iteritems():
							position = str(wirelessmenu.get_position())
							if str(detail['Network']['menu']) == position:
								ssid = network

						ssidconfig = netconfdir +ssid +".conf"
						if not os.path.exists(ssidconfig):
							writeconfig()
						modal("Connecting...","false")
						connect()
						drawinterfacestatus()

		pygame.display.update()
