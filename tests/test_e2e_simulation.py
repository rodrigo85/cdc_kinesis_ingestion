"""End-to-end simulation test verifying PostgreSQL data flowing through CDC transform."""

import base64
import json
import psycopg2
import pytest
from psycopg2.extras import RealDictCursor

from lambda_transform.transform import lambda_handler


def test_postgres_to_lambda_transform_e2e() -> None:
    # 1. Fetch latest record inserted into PostgreSQL
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="delivery_db",
        user="postgres",
        password="postgres",
    )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM delivery.orders ORDER BY id DESC LIMIT 1;")
        row = cur.fetchone()
    conn.close()

    assert row is not None, "PostgreSQL should contain orders created by stream_producer!"

    # 2. Simulate AWS DMS CDC JSON payload
    dms_cdc_event = {
        "data": {
            "id": row["id"],
            "order_number": row["order_number"],
            "customer_name": row["customer_name"],
            "status": row["status"],
            "total_amount": float(row["total_amount"]),
            "payment_status": row["payment_status"],
            "delivery_address": row["delivery_address"],
            "driver_id": row["driver_id"],
            "restaurant_id": row["restaurant_id"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        },
        "metadata": {
            "timestamp": "2026-10-14T15:20:31.960177Z",
            "record-type": "data",
            "operation": "insert",
            "partition-key-type": "schema-table",
            "schema-name": "delivery",
            "table-name": "orders",
            "transaction-id": 789123,
        },
    }

    # 3. Simulate Kinesis Firehose wrapping
    encoded_dms_data = base64.b64encode(json.dumps(dms_cdc_event).encode("utf-8")).decode("utf-8")
    firehose_event = {
        "invocationId": "inv-test-e2e",
        "deliveryStreamArn": "arn:aws:firehose:sa-east-1:123456789012:deliverystream/cdc-delivery",
        "region": "sa-east-1",
        "records": [
            {
                "recordId": "rec-e2e-001",
                "approximateArrivalTimestamp": 1791991232000,
                "data": encoded_dms_data,
            }
        ],
    }

    # 4. Invoke Lambda Handler
    response = lambda_handler(firehose_event, None)

    # 5. Assertions
    assert "records" in response
    assert len(response["records"]) == 1
    out_record = response["records"][0]

    assert out_record["recordId"] == "rec-e2e-001"
    assert out_record["result"] == "Ok"

    # Decode and verify NDJSON format
    raw_output = base64.b64decode(out_record["data"]).decode("utf-8")
    assert raw_output.endswith("\n"), "Must terminate with \\n for Athena / S3 NDJSON!"

    parsed_output = json.loads(raw_output.strip())
    assert parsed_output["id"] == row["id"]
    assert parsed_output["order_number"] == row["order_number"]
    assert parsed_output["status"] == row["status"]
    assert parsed_output["_cdc_op"] == "insert"
    assert parsed_output["_cdc_table"] == "delivery.orders"
    assert parsed_output["_cdc_tx_id"] == 789123
    assert "_cdc_ingested_at" in parsed_output
    print(f"\n[E2E SUCCESS] Successfully validated transformed record: {parsed_output}")
