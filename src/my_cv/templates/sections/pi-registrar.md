# pi_registrar — authenticated IP address registrar

Built a client-server service that records hosts’ current IPv4 and IPv6 addresses
against their certificate identities. The client creates a signed JSON Web Token
from its certificate and submits it over HTTPS; the server validates the certificate
against a configured certificate authority before accepting the registration.

- **Address registration:** Supports IPv4 and IPv6, with a client that can resolve
  and connect using either address family.
- **Storage and DNS:** Keeps the latest registered address and timestamp in SQLite,
  and can optionally update DNS records using authenticated dynamic DNS.
- **Deployment:** Includes systemd service and timer packages for Debian and Arch
  Linux, so the client can periodically refresh a host’s address.
- **Core technologies:** Python, CherryPy, HTTPS, X.509/PKI, JWT, SQLite, DNS,
  systemd, Debian packaging, and Arch Linux packaging.

[View the project on GitHub](https://github.com/vintozver/pi_registrar/)
