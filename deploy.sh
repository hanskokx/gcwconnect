#! /bin/bash
chmod +x build/wificonfig.py
rm wificonfig.opk
mksquashfs build/* wificonfig.opk -noappend -comp gzip -all-root
scp wificonfig.opk zero:/media/data/apps/