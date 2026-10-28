# Blackbox

Share folders of a Linux host over the internet, without VPN.

- **WebDAV** over HTTPS (`rclone serve webdav`), reachable from the public IP.
- **Samba** on the LAN, SMB3 with encryption.
- **Status panel** on port `6680` (read-only): disk standby state in real time and space used by each Blackbox.

Sources are installed once in `/opt/blackbox`. Every user of the host has their own configuration in `~/.blackboxrc`, their own WebDAV instance (`blackbox-webdav@<user>`) and their own Samba share, with the same credentials. No anonymous access.

## Installation

Once per host:

```shell
sudo git clone https://github.com/francescobianco/blackbox /opt/blackbox
sudo make -C /opt/blackbox install
```

Then each user:

```shell
sudo make -C /opt/blackbox configure
```

The first run creates `~/.blackboxrc` and stops asking for `BLACKBOX_PASSWORD`. Set it and run `configure` again.

On the router, forward TCP `BLACKBOX_WEBDAV_PORT` of each user from the public IP to the Blackbox host.

## Configuration

`~/.blackboxrc` (created from [`.blackboxrc.example`](.blackboxrc.example), `chmod 600` since it holds credentials):

| Variable | Default | Used for |
|---|---|---|
| `BLACKBOX_DIR` | `$HOME/Blackbox` | Folder shared via WebDAV and Samba |
| `BLACKBOX_USER` | `$USER` | Login |
| `BLACKBOX_PASSWORD` | *(required)* | Password |
| `BLACKBOX_SHARE` | `$USER` | Samba share name, unique among users |
| `BLACKBOX_WEBDAV_PORT` | `6661` | WebDAV HTTPS port, unique among users |

After editing it, apply with `sudo make -C /opt/blackbox configure`. To remove your Blackbox (keeps `~/.blackboxrc` and the folder): `sudo make -C /opt/blackbox unconfigure`.

Generated files live in `/etc/blackbox/users/<user>/`.

## Connecting

- WebDAV: `davs://<user>@<public-ip>:<port>/` (the certificate is self-signed: accept it on first connection)
- Samba (LAN): `smb://<host>/<share>`
- Status (LAN): `http://<host>:6680/`, read-only, no login: do not forward it on the router

## Read more

- <https://rclone.org/commands/rclone_serve_webdav/>
