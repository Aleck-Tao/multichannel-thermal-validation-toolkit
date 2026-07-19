"""Public, synthetic-data toolkit for multichannel thermal validation."""

from .analysis import analyze_experiment
from .models import ChannelMetrics, ValidationIssue, ValidationReport
from .protocol_x import ProtocolError, SampleRecord, Status, decode_sample, encode_sample

__all__ = [
    "ChannelMetrics",
    "ProtocolError",
    "SampleRecord",
    "Status",
    "ValidationIssue",
    "ValidationReport",
    "analyze_experiment",
    "decode_sample",
    "encode_sample",
]
