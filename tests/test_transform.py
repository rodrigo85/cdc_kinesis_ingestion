"""Comprehensive unit test suite for the CDC Firehose Lambda Transformation."""

import base64
import json
import pytest
from typing import Any, Dict

from lambda_transform.models import FirehoseRecordStatus
from lambda_transform.transform import (
    lambda_handler,
    process_record,
    transform_dms_payload,
)


@pytest.fixture
def sample_dms_insert_payload() -> Dict[str, Any]:
    return {
        "data": {
            "id": 29,
            "order_number": "2156422",
            "customer_name": "Jane Smith",
            "status": "Preparing",
            "total_amount": 30.75,
            "payment_status": "Paid",
            "delivery_address": "456 Elm St, Springfield",
            "driver_id": 2,
            "restaurant_id": 3,
        },
        "metadata": {
            "timestamp": "2024-12-16T13:24:38.504090Z",
            "record-type": "data",
            "operation": "insert",
            "partition-key-type": "schema-table",
            "schema-name": "delivery",
            "table-name": "orders",
            "transaction-id": 554249,
        },
    }


@pytest.fixture
def sample_dms_update_payload() -> Dict[str, Any]:
    return {
        "data": {
            "id": 29,
            "order_number": "2156422",
            "customer_name": "Jane Smith",
            "status": "Delivered",
            "total_amount": 30.75,
            "payment_status": "Paid",
        },
        "metadata": {
            "timestamp": "2024-12-16T13:45:00.000000Z",
            "record-type": "data",
            "operation": "update",
            "schema-name": "delivery",
            "table-name": "orders",
            "transaction-id": 554255,
        },
    }


@pytest.fixture
def sample_dms_control_payload() -> Dict[str, Any]:
    return {
        "control": {"type": "HEARTBEAT"},
        "metadata": {
            "record-type": "control",
            "timestamp": "2024-12-16T14:00:00.000000Z",
        },
    }


def encode_payload(payload: Dict[str, Any]) -> str:
    """Helper to convert dict to base64 encoded JSON string."""
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def decode_output_data(b64_str: str) -> Dict[str, Any]:
    """Helper to decode Firehose transformed data output."""
    raw = base64.b64decode(b64_str).decode("utf-8")
    assert raw.endswith("\n"), "Output record MUST end with newline delimiter for S3 NDJSON!"
    return json.loads(raw.strip())


class TestTransformDmsPayload:
    """Unit tests for DMS payload processing logic."""

    def test_flattened_insert(self, sample_dms_insert_payload: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FLATTEN_PAYLOAD", "true")
        status, result = transform_dms_payload(sample_dms_insert_payload)

        assert status == FirehoseRecordStatus.OK
        assert result is not None
        assert result["id"] == 29
        assert result["order_number"] == "2156422"
        assert result["_cdc_op"] == "insert"
        assert result["_cdc_table"] == "delivery.orders"
        assert result["_cdc_tx_id"] == 554249
        assert "_cdc_ingested_at" in result

    def test_unflattened_envelope(self, sample_dms_insert_payload: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("lambda_transform.transform.FLATTEN_PAYLOAD", False)
        status, result = transform_dms_payload(sample_dms_insert_payload)

        assert status == FirehoseRecordStatus.OK
        assert result is not None
        assert "data" in result
        assert "metadata" in result
        assert result["data"]["customer_name"] == "Jane Smith"
        assert "_cdc_ingested_at" in result

    def test_drop_control_records(self, sample_dms_control_payload: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("lambda_transform.transform.DROP_CONTROL_RECORDS", True)
        status, result = transform_dms_payload(sample_dms_control_payload)

        assert status == FirehoseRecordStatus.DROPPED
        assert result is None


class TestProcessRecord:
    """Unit tests for single Firehose record processing."""

    def test_successful_insert_processing(self, sample_dms_insert_payload: Dict[str, Any]) -> None:
        record = {
            "recordId": "rec-001",
            "approximateArrivalTimestamp": 1700000000,
            "data": encode_payload(sample_dms_insert_payload),
        }

        response = process_record(record)
        assert response["recordId"] == "rec-001"
        assert response["result"] == "Ok"

        decoded = decode_output_data(response["data"])
        assert decoded["order_number"] == "2156422"
        assert decoded["_cdc_op"] == "insert"

    def test_control_record_dropped(self, sample_dms_control_payload: Dict[str, Any]) -> None:
        record = {
            "recordId": "rec-ctrl-001",
            "approximateArrivalTimestamp": 1700000000,
            "data": encode_payload(sample_dms_control_payload),
        }

        response = process_record(record)
        assert response["recordId"] == "rec-ctrl-001"
        assert response["result"] == "Dropped"

    def test_corrupted_base64_routes_to_processing_failed(self) -> None:
        record = {
            "recordId": "rec-bad-001",
            "approximateArrivalTimestamp": 1700000000,
            "data": "This_is_not_valid_base64!!!",
        }

        response = process_record(record)
        assert response["recordId"] == "rec-bad-001"
        assert response["result"] == "ProcessingFailed"

    def test_invalid_json_routes_to_processing_failed(self) -> None:
        bad_json_b64 = base64.b64encode(b"{ malformed json string").decode("utf-8")
        record = {
            "recordId": "rec-bad-002",
            "approximateArrivalTimestamp": 1700000000,
            "data": bad_json_b64,
        }

        response = process_record(record)
        assert response["recordId"] == "rec-bad-002"
        assert response["result"] == "ProcessingFailed"

    def test_oversized_payload_fails(self, sample_dms_insert_payload: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("lambda_transform.transform.MAX_DATA_SIZE", 50)  # artificially low
        record = {
            "recordId": "rec-oversize-001",
            "approximateArrivalTimestamp": 1700000000,
            "data": encode_payload(sample_dms_insert_payload),
        }

        response = process_record(record)
        assert response["recordId"] == "rec-oversize-001"
        assert response["result"] == "ProcessingFailed"


class TestLambdaHandlerBatch:
    """Integration test for full Firehose batch handling."""

    def test_mixed_batch(
        self,
        sample_dms_insert_payload: Dict[str, Any],
        sample_dms_update_payload: Dict[str, Any],
        sample_dms_control_payload: Dict[str, Any],
    ) -> None:
        event = {
            "invocationId": "inv-12345",
            "deliveryStreamArn": "arn:aws:firehose:sa-east-1:123456789012:deliverystream/test",
            "region": "sa-east-1",
            "records": [
                {
                    "recordId": "r1",
                    "approximateArrivalTimestamp": 1700000000,
                    "data": encode_payload(sample_dms_insert_payload),
                },
                {
                    "recordId": "r2",
                    "approximateArrivalTimestamp": 1700000001,
                    "data": encode_payload(sample_dms_update_payload),
                },
                {
                    "recordId": "r3",
                    "approximateArrivalTimestamp": 1700000002,
                    "data": encode_payload(sample_dms_control_payload),
                },
                {
                    "recordId": "r4",
                    "approximateArrivalTimestamp": 1700000003,
                    "data": "bad_data_triggering_failure",
                },
            ],
        }

        response = lambda_handler(event, None)
        assert "records" in response
        assert len(response["records"]) == 4

        results = {r["recordId"]: r["result"] for r in response["records"]}
        assert results["r1"] == "Ok"
        assert results["r2"] == "Ok"
        assert results["r3"] == "Dropped"
        assert results["r4"] == "ProcessingFailed"
