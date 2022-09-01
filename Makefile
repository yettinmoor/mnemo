INSTALL_DIR:=${HOME}/.local/bin

install: mnemo.py
	sed '1i#!/usr/bin/env python3' $^ > ${INSTALL_DIR}/mnemo
	chmod +x ${INSTALL_DIR}/mnemo
