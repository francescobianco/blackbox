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

## Let's Encrypt

Clients that reject self-signed certificates (e.g. FRITZ!Box online storage) need a trusted one:

1. Point a DNS `A` record of your domain (e.g. `blackbox.example.com`) to the public IP.
2. On the router, forward TCP 80 to the Blackbox host (used only by `certbot` to validate the domain; nothing else may listen on port 80).
3. Set `BLACKBOX_DOMAIN` (and optionally `BLACKBOX_EMAIL`) in `~/.blackboxrc` and run `sudo make -C /opt/blackbox configure`.

If port 80 cannot be forwarded, validate via DNS instead: create a subdomain on [DuckDNS](https://www.duckdns.org), add the record `_acme-challenge.<domain> CNAME <subdomain>.duckdns.org` to your domain, and set `BLACKBOX_DUCKDNS_DOMAIN` and `BLACKBOX_DUCKDNS_TOKEN`.

The certificate is renewed by the `certbot` timer, which copies it to `/etc/blackbox/users/<user>/` and restarts the WebDAV service.

## Configuration

`~/.blackboxrc` (created from [`.blackboxrc.example`](.blackboxrc.example), `chmod 600` since it holds credentials):

| Variable | Default | Used for |
|---|---|---|
| `BLACKBOX_DIR` | `$HOME/Blackbox` | Folder shared via WebDAV and Samba |
| `BLACKBOX_USER` | `$USER` | Login |
| `BLACKBOX_PASSWORD` | *(required)* | Password |
| `BLACKBOX_SHARE` | `$USER` | Samba share name, unique among users |
| `BLACKBOX_WEBDAV_PORT` | `6661` | WebDAV HTTPS port, unique among users |
| `BLACKBOX_DOMAIN` | *(empty)* | Public domain for a Let's Encrypt certificate; empty means self-signed |
| `BLACKBOX_EMAIL` | *(empty)* | Email for Let's Encrypt expiry notices |
| `BLACKBOX_DUCKDNS_DOMAIN` | *(empty)* | DuckDNS subdomain for DNS validation, when port 80 cannot be forwarded |
| `BLACKBOX_DUCKDNS_TOKEN` | *(empty)* | DuckDNS token |

After editing it, apply with `sudo make -C /opt/blackbox configure`. To remove your Blackbox (keeps `~/.blackboxrc` and the folder): `sudo make -C /opt/blackbox unconfigure`.

Generated files live in `/etc/blackbox/users/<user>/`.

## Connecting

- WebDAV: `davs://<user>@<domain>:<port>/` (without `BLACKBOX_DOMAIN`, use the public IP and accept the self-signed certificate on first connection)
- Samba (LAN): `smb://<host>/<share>`
- Status (LAN): `http://<host>:6680/`, read-only, no login: do not forward it on the router

## Read more

- <https://rclone.org/commands/rclone_serve_webdav/>
