# Recovery Model

Recovery is deliberately separated into three levels.

1. User state: restore user-accessible files and application state from backups.
2. Lokivolt state: restore a previously verified Lokivolt release through its supported recovery/update mechanism.
3. OEM firmware: restore the exact official firmware package for the device variant.

The engine never treats an incomplete Termux file copy as a complete system-image backup.

A recovery plan is always generated with an explicit authorization requirement. The planner must reject an image when its hash, device family, boot state or rollback requirements do not match.

Rollback protection belongs to the platform trust model; keeping old bytes alone does not guarantee that the bootloader will accept them.
