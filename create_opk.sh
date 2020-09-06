#! /bin/sh

python -m py_compile gcwconnect.py
cp __pycache__/gcwconnect*.pyc gcwconnect.pyc
mksquashfs \
	default.gcw0.desktop \
	gcwconnect.pyc \
	icon.png \
	data \
	gcwconnect.opk -noappend -no-exports -no-xattrs -all-root
rm gcwconnect.pyc
