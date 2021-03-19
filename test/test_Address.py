from gcwconnect import App

app = App()
ip = "192.168.1.100"

# Test IP addresses
def test_ip_is_valid():
  test = app.Address.ip(ip=ip)
  assert(test) is ip

def test_ipv6_is_invalid():
  ipv6 = "7ffb:e790:ab68:c05b:6e0b:9bdf:48dc:43b4"
  test = app.Address.ip(ip=ipv6)
  assert(test) is None

def test_ip_is_empty():
  test = app.Address.ip()
  assert(test) is None

def test_ip_is_malformed():
  test = app.Address.ip(ip="abc")
  assert(test) is None

# Test Mac addresses
def test_mac_is_valid():
  mac = "55:42:F4:F4:BA:16"
  test = app.Address.mac(mac=mac)
  assert(test) is mac

def test_mac_is_invalid():
  test = app.Address.mac(mac="abc")
  assert(test) is False

def test_mac_is_empty():
  test = app.Address.mac()
  assert(test) is False

def test_mac_is_malformed():
  mac = "definitely:not:a:mac"
  test = app.Address.mac(mac=mac)
  assert(test) is False

def test_mac_is_malformed_with_missing_semicolons():
  mac = "0e-43-16-c1-05-5c"
  test = app.Address.mac(mac=mac)
  assert(test) is False


def test_mac_is_malformed_with_incorrect_separator():
  mac = "0e43.16c1.055c"
  test = app.Address.mac(mac=mac)
  assert(test) is False
