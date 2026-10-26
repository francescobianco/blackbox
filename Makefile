USER := $(or $(SUDO_USER),$(shell logname 2>/dev/null),$(shell id -un))
HOME_DIR := $(shell getent passwd $(USER) | cut -d: -f6)
RC := $(HOME_DIR)/.blackboxrc
ETC := /etc/blackbox/users/$(USER)
SRC := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# Load ~/.blackboxrc into the recipe shell
LOAD := set -a; USER=$(USER); HOME=$(HOME_DIR); . $(RC); set +a
VARS := $$USER $$BLACKBOX_DIR $$BLACKBOX_SHARE

# System-wide, once per host
install:
	@apt-get install -y samba gettext rclone apache2-utils openssl
	@if [ -f /etc/samba/smb.conf ] && [ ! -f /etc/samba/smb_0.conf ]; then mv /etc/samba/smb.conf /etc/samba/smb_0.conf; fi
	@mkdir -p /etc/blackbox/users
	@cp $(SRC)blackbox-webdav@.service /etc/systemd/system/
	@systemctl daemon-reload
	@$(MAKE) -f $(SRC)Makefile samba
	@echo Blackbox is installed. Each user runs: sudo make -C $(SRC) configure

# Rebuild Samba config from the global part and every user's share
samba:
	@cat $(SRC)smb.conf /etc/blackbox/users/*/share.conf > /etc/samba/smb.conf 2>/dev/null || true
	@cat /etc/blackbox/users/*/map > /etc/samba/blackbox.map 2>/dev/null || true
	@service smbd restart

# Per user: apply ~/.blackboxrc of the user running sudo
config:
	@if [ ! -f $(RC) ]; then cp $(SRC).blackboxrc.example $(RC); chown $(USER):$(USER) $(RC); echo Created $(RC); fi
	@chmod 600 $(RC)
	@$(LOAD); if [ -z "$$BLACKBOX_USER" ] || [ -z "$$BLACKBOX_PASSWORD" ]; then echo "Set BLACKBOX_USER and BLACKBOX_PASSWORD in $(RC)"; exit 1; fi
	@$(LOAD); if grep -lx "BLACKBOX_WEBDAV_PORT=$$BLACKBOX_WEBDAV_PORT" /etc/blackbox/users/*/env 2>/dev/null | grep -v "^$(ETC)/"; then echo "Port $$BLACKBOX_WEBDAV_PORT is used by another user"; exit 1; fi
	@$(LOAD); if grep -lx "\[$$BLACKBOX_SHARE\]" /etc/blackbox/users/*/share.conf 2>/dev/null | grep -v "^$(ETC)/"; then echo "Share $$BLACKBOX_SHARE is used by another user"; exit 1; fi

configure: config
	@mkdir -p $(ETC)
	@$(LOAD); if [ ! -d "$$BLACKBOX_DIR" ]; then mkdir -p "$$BLACKBOX_DIR"; chown $(USER):$(USER) "$$BLACKBOX_DIR"; fi
	@$(LOAD); printf 'BLACKBOX_DIR="%s"\nBLACKBOX_WEBDAV_PORT=%s\n' "$$BLACKBOX_DIR" "$$BLACKBOX_WEBDAV_PORT" > $(ETC)/env
	@$(LOAD); printf '%s\n' "$$BLACKBOX_PASSWORD" | htpasswd -iBc $(ETC)/htpasswd "$$BLACKBOX_USER"
	@if [ ! -f $(ETC)/tls.crt ]; then openssl req -x509 -newkey rsa:4096 -nodes -days 3650 -subj "/CN=$$(hostname)" -keyout $(ETC)/tls.key -out $(ETC)/tls.crt 2>/dev/null; fi
	@chown root:$(USER) $(ETC)/htpasswd $(ETC)/tls.key
	@chmod 640 $(ETC)/htpasswd $(ETC)/tls.key
	@$(LOAD); envsubst '$(VARS)' < $(SRC)share.conf > $(ETC)/share.conf
	@$(LOAD); echo "$(USER) = $$BLACKBOX_USER" > $(ETC)/map
	@$(LOAD); printf '%s\n%s\n' "$$BLACKBOX_PASSWORD" "$$BLACKBOX_PASSWORD" | smbpasswd -s -a $(USER) >/dev/null
	@$(MAKE) -f $(SRC)Makefile samba
	@systemctl enable blackbox-webdav@$(USER)
	@systemctl restart blackbox-webdav@$(USER)
	@echo Blackbox configured for $(USER) from $(RC).

# Per user: remove the user's Blackbox (keeps ~/.blackboxrc and the shared folder)
unconfigure:
	@systemctl disable --now blackbox-webdav@$(USER) 2>/dev/null || true
	@smbpasswd -x $(USER) >/dev/null 2>&1 || true
	@rm -rf $(ETC)
	@$(MAKE) -f $(SRC)Makefile samba
	@echo Blackbox removed for $(USER).
