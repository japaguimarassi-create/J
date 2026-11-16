# Supplied JAR audit — DualLong HyperCore 0.1.0

## Exact inputs
| Artifact | Detected mod ID | Version |
|---|---|---|
| DragonBlockC-v1.4.85.jar | jinryuudragonblockc | 1.4.85 |
| JRMCore-v1.3.51.jar | jinryuujrmcore | 1.3.51 |
| JBRA-Client-v1.6.52.jar | jinryuubetterrenderaddon | 1.6.52 |
| dbcexpansion-1.3.2.jar | dbcexpansion | 1.3.2 |
| npcdbc-1.2.1.jar | npcdbc | 1.2.1 |
| dbc-CreatureBoost-0.1.1.jar | dbccb | mcmod.info reports 0.0.2; annotation contains a dirty build string |
| ninjinentities-Unofficial-1.4.5.jar | ninjinentities | 1.4.5 |

## Numeric findings
Bytecode inspection (`javap -p -s`) of the supplied JRMCore 1.3.51 JAR found legacy `int` contracts in player and stat classes, including:
- `JinRyuu.JRMCore.server.JGPlayerMP`: `getAttributes(): int[]`, `getLevel(int[]): int`, stat/health/energy/stamina accessors returning `int`, and mutators accepting `int`.
- `JinRyuu.JRMCore.p.JRMCorePStats`: current body, energy and stamina fields are `int`; constructor descriptor `(IIIBB)V`.
- `JinRyuu.JRMCore.p.JRMCorePStats2`: TP and experience are `int`; player attributes use `int[]`; constructor descriptor `(IIB[I)V`.
- `JinRyuu.JRMCore.p.DBC.DBCPtick`: legacy integer state is present in the network message path.
- `JinRyuu.JRMCore.JRMCoreH`: legacy static integer fields and an `HashMap<String,Integer>` are present.

The audit demonstrates where 32-bit contracts exist; it does not establish every call path or prove that each gameplay metric can be safely widened in isolation.

## Compatibility decision
Do not globally rewrite `int` opcodes, field descriptors, method descriptors, arrays or packet layouts. That would be binary-incompatible and could corrupt third-party mods. This release stores extended values in a separate NBT compound using two longs per signed 128-bit value. The identity transformer only observes selected class loads; it returns the original byte array unchanged.

## Uploaded JAR fingerprints (SHA-256)
- DBC: `be8c849ab107b1126018bc5b0d0d254d751129f70f3349261f1469f0c220dc9d`
- JRMCore: `0614265d665b6e60456d460255c1488377cad1200ad6bd9444128d835fc28946`
- JBRA: `541bc7a8063879e897a27acc3a5850b02a15f8e23ee086cb8d03a36a76e23634`
- DBC Expansion: `ef2e6a3dcbeb49c4dcf444aee38d32ccc1f2d5f21f49edace5145af7b909d2a5`
- NPCDBC: `ba99440ffa25d52b10d02a54d1595777f98edb7a3c25f9ca914b88694b7ed52f`
- CreatureBoost: `ebc566d946a463a98d3c5821d3a4c44a1c6ae53c4628cd3a1132170fb6e3571d`
- Ninjin Entities: `090ce2bbb554f7aadc652567a878988a625767b81e45522cdd4384c302c0eed4`
