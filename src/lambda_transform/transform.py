"""AWS Lambda Transformation handler for DMS CDC records consumed via Kinesis Firehose.

This module decodes CDC records emitted by AWS DMS, filters control messages,
optionally flattens the envelope for direct Athena / Presto / Spark queryability,
appends standard newline delimiters for NDJSON compliance in S3, and ensures
safe dead-letter routing on processing errors.
"""

import base64
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from lambda_transform.logger import get_logger
from lambda_transform.models import (
    FirehoseEvent,
    FirehoseRecord,
    FirehoseRecordStatus,
    FirehoseResponse,
    FirehoseTransformedRecord,
)

logger = get_logger("firehose-cdc-transform")

# Configuration via environment variables
MAX_DATA_SIZE = int(os.environ.get("MAX_DATA_SIZE", 1024 * 1024))  # 1MB limit per record
FLATTEN_PAYLOAD = os.environ.get("FLATTEN_PAYLOAD", "true").lower() in ("true", "1", "yes")
DROP_CONTROL_RECORDS = os.environ.get("DROP_CONTROL_RECORDS", "true").lower() in ("true", "1", "yes")


def transform_dms_payload(raw_payload: Dict[str, Any]) -> Tuple[FirehoseRecordStatus, Optional[Dict[str, Any]]]:
    """Processes a single DMS payload dictionary.

    Returns:
        Tuple of (status, processed_data_dict)
    """
    metadata: Dict[str, Any] = raw_payload.get("metadata", {})
    record_type = metadata.get("record-type", "data")

    # Filter out DMS control records / heartbeats if configured
    if record_type == "control" or "control" in raw_payload:
        if DROP_CONTROL_RECORDS:
            return FirehoseRecordStatus.DROPPED, None

    # Determine data payload
    data: Dict[str, Any] = raw_payload.get("data", {})
    operation = metadata.get("operation", "unknown").lower()
    schema_name = metadata.get("schema-name", "")
    table_name = metadata.get("table-name", "")
    full_table = f"{schema_name}.{table_name}".strip(".")
    tx_id = metadata.get("transaction-id")
    source_ts = metadata.get("timestamp")

    ingestion_ts = datetime.now(timezone.utc).isoformat()

    if FLATTEN_PAYLOAD and isinstance(data, dict):
        # Flattened format for high-performance BigQuery / Athena / Snowflake queries
        flattened: Dict[str, Any] = dict(data)
        flattened["_cdc_op"] = operation
        flattened["_cdc_timestamp"] = source_ts
        flattened["_cdc_table"] = full_table
        flattened["_cdc_tx_id"] = tx_id
        flattened["_cdc_ingested_at"] = ingestion_ts
        return FirehoseRecordStatus.OK, flattened

    # Preserved envelope format
    enriched_envelope = {
        "data": data,
        "metadata": metadata,
        "_cdc_ingested_at": ingestion_ts,
    }
    return FirehoseRecordStatus.OK, enriched_envelope


def process_record(record: FirehoseRecord) -> FirehoseTransformedRecord:
    """Decodes, transforms, and re-encodes a single Firehose record."""
    record_id = record.get("recordId", "unknown")

    try:
        raw_b64 = record.get("data", "")
        if not raw_b64:
            raise ValueError("Empty data field in record")

        decoded_bytes = base64.b64decode(raw_b64)
        raw_payload = json.loads(decoded_bytes.decode("utf-8"))

        status, transformed_data = transform_dms_payload(raw_payload)

        if status == FirehoseRecordStatus.DROPPED or transformed_data is None:
            # Dropped records still require original or empty data according to Firehose spec
            return {
                "recordId": record_id,
                "result": FirehoseRecordStatus.DROPPED.value,
                "data": record.get("data", ""),
            }

        # IMPORTANT: Append newline (\n) for valid NDJSON (Newline Delimited JSON).
        # Without \n, Firehose concatenates records into an invalid single JSON line!
        json_output = json.dumps(transformed_data, default=str) + "\n"
        encoded_data = base64.b64encode(json_output.encode("utf-8")).decode("utf-8")

        if len(encoded_data) > MAX_DATA_SIZE:
            raise ValueError(f"Record payload size ({len(encoded_data)} bytes) exceeds limit ({MAX_DATA_SIZE} bytes)")

        return {
            "recordId": record_id,
            "result": FirehoseRecordStatus.OK.value,
            "data": encoded_data,
        }

    except Exception as exc:
        logger.error(
            f"Failed to process record {record_id}: {exc}",
            extra={"record_id": record_id, "error": str(exc)},
            exc_info=True,
        )
        # Big Tech practice: Set result to 'ProcessingFailed' so Firehose routes
        # failed records to the S3 processing-failed error prefix instead of silently dropping data!
        return {
            "recordId": record_id,
            "result": FirehoseRecordStatus.PROCESSING_FAILED.value,
            "data": record.get("data", ""),
        }


def lambda_handler(event: FirehoseEvent, context: Any) -> FirehoseResponse:
    """AWS Lambda entry point invoked by Kinesis Data Firehose."""
    start_time = time.time()
    records: List[FirehoseRecord] = event.get("records", [])

    transformed_records: List[FirehoseTransformedRecord] = []
    stats = {
        FirehoseRecordStatus.OK.value: 0,
        FirehoseRecordStatus.DROPPED.value: 0,
        FirehoseRecordStatus.PROCESSING_FAILED.value: 0,
    }

    for record in records:
        transformed = process_record(record)
        transformed_records.append(transformed)
        stats[transformed["result"]] = stats.get(transformed["result"], 0) + 1

    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        "Firehose batch processed",
        extra={
            "batch_size": len(records),
            "ok": stats[FirehoseRecordStatus.OK.value],
            "dropped": stats[FirehoseRecordStatus.DROPPED.value],
            "failed": stats[FirehoseRecordStatus.PROCESSING_FAILED.value],
            "duration_ms": elapsed_ms,
        },
    )

    return {"records": transformed_records}
