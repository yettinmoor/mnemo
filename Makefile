INSTALL_DIR:=${HOME}/.local/bin

mnemo: *.py
	zip $@ $^
	mv $@.zip $@

install: mnemo
	sed '1i#!/usr/bin/env python3' mnemo > ${INSTALL_DIR}/mnemo
	chmod +x ${INSTALL_DIR}/mnemo

clean:
	rm mnemo
