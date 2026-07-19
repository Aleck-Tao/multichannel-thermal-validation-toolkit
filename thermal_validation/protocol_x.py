"""A deliberately fictional binary protocol used for public demonstrations.

Protocol-X is not copied from a commercial device. It uses conventional framing
and CRC-16/CCITT solely to exercise integrity checks and status-first decoding.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntFlag


START_BYTE = 0xA5
VERSION = 1
MESSAGE_SAMPLE = 0x10
HEADER = struct.Struct(">BBBHH")
SAMPLE = struct.Struct(">IBBi")
CRC = struct.Struct(">H")


class ProtocolError(ValueError):
    """Raised when a frame is malformed, unsupported, or fails integrity checks."""


class Status(IntFlag):
    VALID = 0
    SENSOR_OPEN = 1 << 0
    OUT_OF_RANGE = 1 << 1
    STALE = 1 << 2
    INTERNAL_FAULT = 1 << 3


@dataclass(frozen=True)
class SampleRecord:
    sequence: int
    timestamp_ms: int
    channel: int
    status: Status
    temperature_c: float | None

    @property
    def usable(self) -> bool:
        return self.status == Status.VALID and self.temperature_c is not None


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    crc = initial
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode_sample(
    *, sequence: int, timestamp_ms: int, channel: int, status: Status, temperature_c: float
) -> bytes:
    if not 0 <= sequence <= 0xFFFF:
        raise ValueError("sequence must fit uint16")
    if not 0 <= timestamp_ms <= 0xFFFFFFFF:
        raise ValueError("timestamp_ms must fit uint32")
    if not 0 <= channel <= 0xFF:
        raise ValueError("channel must fit uint8")
    milli_celsius = round(temperature_c * 1000)
    payload = SAMPLE.pack(timestamp_ms, channel, int(status), milli_celsius)
    body = HEADER.pack(START_BYTE, VERSION, MESSAGE_SAMPLE, sequence, len(payload)) + payload
    return body + CRC.pack(crc16_ccitt(body))


def decode_sample(frame: bytes) -> SampleRecord:
    minimum = HEADER.size + SAMPLE.size + CRC.size
    if len(frame) < minimum:
        raise ProtocolError(f"truncated frame: expected at least {minimum} bytes")

    start, version, message_type, sequence, payload_length = HEADER.unpack_from(frame)
    if start != START_BYTE:
        raise ProtocolError("invalid start byte")
    if version != VERSION:
        raise ProtocolError(f"unsupported version: {version}")
    if message_type != MESSAGE_SAMPLE:
        raise ProtocolError(f"unexpected message type: {message_type}")
    expected_length = HEADER.size + payload_length + CRC.size
    if len(frame) != expected_length:
        raise ProtocolError(f"length mismatch: header declares {expected_length} bytes")
    if payload_length != SAMPLE.size:
        raise ProtocolError(f"unexpected sample payload length: {payload_length}")

    observed_crc = CRC.unpack_from(frame, len(frame) - CRC.size)[0]
    expected_crc = crc16_ccitt(frame[:-CRC.size])
    if observed_crc != expected_crc:
        raise ProtocolError("CRC mismatch")

    timestamp_ms, channel, status_value, milli_celsius = SAMPLE.unpack_from(frame, HEADER.size)
    status = Status(status_value)
    temperature = milli_celsius / 1000 if status == Status.VALID else None
    return SampleRecord(sequence, timestamp_ms, channel, status, temperature)
