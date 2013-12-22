#! /bin/bash

## fix pngs
# optipng -strip all -o7 *.png
chmod +x build/wificonfig.py
rm gcwconnect.opk
mksquashfs build/* gcwconnect.opk -noappend -comp gzip -all-root
scp gcwconnect.opk zero:/media/data/apps/