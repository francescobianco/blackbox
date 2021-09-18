
USER := $(shell logname)

dependencies:
	@apt-get install -y samba gettext

restart:
	@service smbd restart

install-script:
	@if [ -f /etc/samba/smb.conf ]; then mv /etc/samba/smb.conf /etc/samba/smb_0.conf; fi
	@USER=$(USER) envsubst < smb.conf > /etc/samba/smb.conf
	@mkdir -p /media/$(USER)/Blackbox
	@chmod 777 -R /media/$(USER)/Blackbox

install: dependencies install-script restart
	@echo Blackbox is ready.
