import unittest

from thermal_validation.protocol_x import (
    ProtocolError,
    Status,
    decode_sample,
    encode_sample,
)


class ProtocolXTests(unittest.TestCase):
    def test_valid_sample_round_trip(self) -> None:
        frame = encode_sample(
            sequence=17,
            timestamp_ms=123_456,
            channel=4,
            status=Status.VALID,
            temperature_c=42.375,
        )
        record = decode_sample(frame)
        self.assertEqual(record.sequence, 17)
        self.assertEqual(record.timestamp_ms, 123_456)
        self.assertEqual(record.channel, 4)
        self.assertAlmostEqual(record.temperature_c or 0.0, 42.375)
        self.assertTrue(record.usable)

    def test_status_is_checked_before_temperature_is_exposed(self) -> None:
        frame = encode_sample(
            sequence=18,
            timestamp_ms=123_556,
            channel=4,
            status=Status.SENSOR_OPEN,
            temperature_c=999.0,
        )
        record = decode_sample(frame)
        self.assertEqual(record.status, Status.SENSOR_OPEN)
        self.assertIsNone(record.temperature_c)
        self.assertFalse(record.usable)

    def test_crc_corruption_is_rejected(self) -> None:
        frame = bytearray(
            encode_sample(
                sequence=1,
                timestamp_ms=100,
                channel=0,
                status=Status.VALID,
                temperature_c=25.0,
            )
        )
        frame[-3] ^= 0x01
        with self.assertRaisesRegex(ProtocolError, "CRC mismatch"):
            decode_sample(bytes(frame))


    def test_truncated_frame_is_rejected(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "truncated"):
            decode_sample(b"\xA5\x01")


if __name__ == "__main__":
    unittest.main()
