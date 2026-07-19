# Protocol-X public specification

Protocol-X is fictional and defined only for this repository. It uses common framing patterns so that integrity and status-handling behavior can be tested without revealing a commercial protocol.

All multibyte fields are unsigned big-endian unless noted otherwise.

| Field | Bytes | Meaning |
|---|---:|---|
| Start | 1 | Constant `0xA5` |
| Version | 1 | Constant `0x01` |
| Message type | 1 | `0x10` for one sample |
| Sequence | 2 | Monotonic frame counter |
| Payload length | 2 | Number of payload bytes |
| Timestamp | 4 | Milliseconds |
| Channel | 1 | Zero-based public channel code |
| Status | 1 | Bit flags below |
| Temperature | 4 | Signed millidegrees Celsius |
| CRC | 2 | CRC-16/CCITT over header and payload |

Status bits:

| Bit | Codename | Decoder behavior |
|---:|---|---|
| 0 | `SENSOR_OPEN` | Keep metadata; withhold temperature |
| 1 | `OUT_OF_RANGE` | Keep metadata; withhold temperature |
| 2 | `STALE` | Keep metadata; withhold temperature |
| 3 | `INTERNAL_FAULT` | Keep metadata; withhold temperature |

`0x00` means `VALID`. The decoder accepts a numeric value for analysis only when the complete status byte is zero.

This layout, the start byte, the message type, and all identifiers are invented. They must not be interpreted as a vendor register map or device-integration guide.
