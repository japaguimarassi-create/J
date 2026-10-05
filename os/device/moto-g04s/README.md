# Moto g04s hardware enablement

Target family: Motorola moto g04s.

Known public evidence is insufficient to declare a flashable Lokivolt phone image. Some public servicing reports and firmware listings associate XT2421-6 variants with Lion and UMS9230-family hardware, but those sources do not replace live device evidence.

## Required evidence

The device target must capture:

- ro.product.model
- ro.product.manufacturer
- ro.product.device
- ro.product.board
- ro.board.platform
- ro.boot.hardware
- ro.boot.slot_suffix
- ro.boot.flash.locked
- ro.boot.verifiedbootstate
- dynamic partition evidence
- block device topology
- AVB metadata
- kernel release and configuration when accessible
- vendor interface compatibility

The target stays blocked until all boot-critical assumptions are validated.

## Build policy

The generic Lokivolt system layer may be built independently. The Moto g04s boot, vendor, dtbo, vbmeta, and super/dynamic-partition artifacts remain device-specific.

No bootloader bypass, FRP bypass, signature bypass, or forced partition write is part of this target.
