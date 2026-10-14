"""Type definitions and models for DMS CDC events and Firehose transformations."""

from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class FirehoseRecordStatus(str, Enum):
    """Allowed Firehose transformation status values."""

    OK = "Ok"
    DROPPED = "Dropped"
    PROCESSING_FAILED = "ProcessingFailed"


class FirehoseRecord(TypedDict):
    """Input record from Kinesis Firehose."""

    recordId: str
    approximateArrivalTimestamp: Optional[int]
    data: str  # Base64 encoded


class FirehoseTransformedRecord(TypedDict):
    """Output record returned to Kinesis Firehose."""

    recordId: str
    result: str  # "Ok" | "Dropped" | "ProcessingFailed"
    data: str  # Base64 encoded


class FirehoseEvent(TypedDict):
    """Complete input event delivered to Lambda by Firehose."""

    invocationId: str
    deliveryStreamArn: str
    region: str
    records: List[FirehoseRecord]


class FirehoseResponse(TypedDict):
    """Response returned from Lambda to Firehose."""

    records: List[FirehoseTransformedRecord]


class DmsMetadata(TypedDict, total=False):
    """Metadata envelope produced by AWS DMS."""

    timestamp: str
    record_type: str  # Often key is 'record-type'
    operation: str
    partition_key_type: str
    schema_name: str
    table_name: str
    transaction_id: Optional[int]
