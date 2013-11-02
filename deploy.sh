#! /bin/bash
chmod +x build/wificonfig.py
rm gcwconnect.opk
mksquashfs build/* gcwconnect.opk -noappend -comp gzip -all-root
scp gcwconnect.opk zero:/media/data/apps/