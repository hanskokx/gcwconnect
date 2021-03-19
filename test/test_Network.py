from gcwconnect import App

app = App()
mac = "55:42:F4:F4:BA:16"
debug = []

debug["ssid"] = "gcwzero-"+mac
app.Address.mac = app.Address.mac(mac=mac)

def test_ssid_is_broadcasting_ap():
  assert app.Address.mac == mac
  assert debug["ssid"] == "gcwzero-"+app.Address.mac
  test = app.Network.ssid(app, debug)
  assert test == debug["ssid"]
