# Skydive Toledo manifest system

Together with James Robinson, implemented a local manifest system with secure,
limited read-only access from outside the site. It tracks active jumpers throughout
the day and displays the current load board, helping jumpers stay informed about
aircraft status.

![Skydive Toledo manifest board](https://manifest.skydivetoledo.com/)

- **Server:** Implemented entirely on a Raspberry Pi 4 Model B, with daily backups
  and a two-step rollout to allow updates with zero downtime.
- **Satellite displays:** Local displays run on Raspberry Pi 2 W devices and connect
  securely to the main server using VNC.

[Open the live manifest system](https://manifest.skydivetoledo.com/)
