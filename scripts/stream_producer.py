#!/usr/bin/env python3
"""Synthetic CDC Stream Producer for PostgreSQL -> AWS DMS Pipeline.

Simulates realistic e-commerce/delivery transactions:
- Creates new orders (INSERT with status='Pending')
- Updates existing orders through lifecycle stages (Pending -> Preparing -> Out for Delivery -> Delivered)
- Simulates edge cases (cancellations and refunds)

Usage:
    python scripts/stream_producer.py --count 20 --rate 2.0
    python scripts/stream_producer.py --continuous --rate 1.0
    python scripts/stream_producer.py --help
"""

import argparse
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


SAMPLE_CUSTOMERS = [
    "Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince",
    "Evan Wright", "Fiona Gallagher", "George Clark", "Hannah Abbott",
    "Ian Malcolm", "Julia Roberts", "Kevin Bacon", "Laura Croft"
]

SAMPLE_STREETS = [
    "Maple Ave", "Oak Rd", "Pine St", "Elm St", "Cedar Blvd",
    "Birch Ln", "Willow St", "Spruce Dr", "Sycamore Pl", "Chestnut Ct"
]

STATUS_SEQUENCE = ["Pending", "Preparing", "Out for Delivery", "Delivered"]


def get_db_connection(args: argparse.Namespace) -> Any:
    """Creates a psycopg2 database connection."""
    if not HAS_PSYCOPG2:
        print("[ERROR] psycopg2-binary is required. Install with: pip install psycopg2-binary")
        sys.exit(1)

    return psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.database,
        user=args.user,
        password=args.password,
    )


def generate_new_order() -> Dict[str, Any]:
    """Generates synthetic initial order data."""
    order_num = f"ORD-{int(time.time())}-{random.randint(1000, 9999)}"
    customer = random.choice(SAMPLE_CUSTOMERS)
    address = f"{random.randint(100, 999)} {random.choice(SAMPLE_STREETS)}, Springfield"
    amount = round(random.uniform(15.0, 120.0), 2)
    restaurant_id = random.randint(1, 10)
    driver_id = random.randint(1, 8)
    estimated_delivery = datetime.now(timezone.utc) + timedelta(minutes=random.randint(25, 60))

    return {
        "order_number": order_num,
        "customer_name": customer,
        "status": "Pending",
        "total_amount": amount,
        "payment_status": "Paid" if random.random() > 0.1 else "Pending",
        "delivery_address": address,
        "delivery_notes": random.choice([
            "Leave at door", "Ring doorbell", "Call on arrival",
            "Gate code: 1234", "Hand to customer", None
        ]),
        "estimated_delivery_time": estimated_delivery,
        "driver_id": driver_id,
        "restaurant_id": restaurant_id,
    }


def insert_order(conn: Any, order: Dict[str, Any]) -> int:
    """Inserts a new order into delivery.orders."""
    query = """
        INSERT INTO delivery.orders (
            order_number, customer_name, status, total_amount, payment_status,
            delivery_address, delivery_notes, estimated_delivery_time, driver_id, restaurant_id
        ) VALUES (
            %(order_number)s, %(customer_name)s, %(status)s, %(total_amount)s, %(payment_status)s,
            %(delivery_address)s, %(delivery_notes)s, %(estimated_delivery_time)s, %(driver_id)s, %(restaurant_id)s
        ) RETURNING id;
    """
    with conn.cursor() as cur:
        cur.execute(query, order)
        order_id = cur.fetchone()[0]
        conn.commit()
    return order_id


def progress_random_order(conn: Any) -> Optional[str]:
    """Updates an existing active order to its next status."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, order_number, status
            FROM delivery.orders
            WHERE status IN ('Pending', 'Preparing', 'Out for Delivery')
            ORDER BY RANDOM()
            LIMIT 1;
        """)
        row = cur.fetchone()

        if not row:
            return None

        current_status = row["status"]
        order_id = row["id"]
        order_number = row["order_number"]

        # Cancel 5% of pending/preparing orders
        if random.random() < 0.05 and current_status in ("Pending", "Preparing"):
            new_status = "Cancelled"
            payment_status = "Refunded"
        else:
            curr_idx = STATUS_SEQUENCE.index(current_status)
            new_status = STATUS_SEQUENCE[curr_idx + 1]
            payment_status = "Paid"

        cur.execute("""
            UPDATE delivery.orders
            SET status = %s, payment_status = %s, updated_at = NOW()
            WHERE id = %s;
        """, (new_status, payment_status, order_id))
        conn.commit()

        return f"Order {order_number} (id={order_id}) updated: {current_status} -> {new_status}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic CDC Stream Producer for PostgreSQL")
    parser.add_argument("--host", default=os.getenv("POSTGRES_HOST", "localhost"), help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=int(os.getenv("POSTGRES_PORT", 5432)), help="PostgreSQL port")
    parser.add_argument("--database", default=os.getenv("POSTGRES_DB", "delivery_db"), help="Database name")
    parser.add_argument("--user", default=os.getenv("POSTGRES_USER", "postgres"), help="Database user")
    parser.add_argument("--password", default=os.getenv("POSTGRES_PASSWORD", "postgres"), help="Database password")
    parser.add_argument("--rate", type=float, default=1.0, help="Events per second (default: 1.0)")
    parser.add_argument("--count", type=int, default=10, help="Number of events to generate (default: 10)")
    parser.add_argument("--continuous", action="store_true", help="Run indefinitely until stopped")
    args = parser.parse_args()

    print(f"[INIT] Connecting to PostgreSQL at {args.host}:{args.port}/{args.database}...")
    try:
        conn = get_db_connection(args)
        print("[SUCCESS] Connected successfully to PostgreSQL.")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        sys.exit(1)

    interval = 1.0 / max(args.rate, 0.01)
    events_generated = 0

    print(f"[START] Producing CDC events (rate={args.rate}/s)... Press Ctrl+C to stop.")
    try:
        while args.continuous or events_generated < args.count:
            # 60% of events are new orders, 40% are status updates
            if random.random() < 0.6:
                order = generate_new_order()
                order_id = insert_order(conn, order)
                print(f"[CDC INSERT] Order {order['order_number']} (id={order_id}) created for {order['customer_name']} (${order['total_amount']})")
            else:
                update_msg = progress_random_order(conn)
                if update_msg:
                    print(f"[CDC UPDATE] {update_msg}")
                else:
                    # No active orders to update, create one instead
                    order = generate_new_order()
                    order_id = insert_order(conn, order)
                    print(f"[CDC INSERT] Order {order['order_number']} (id={order_id}) created (fallback).")

            events_generated += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[STOP] Producer stopped by user.")
    finally:
        conn.close()
        print(f"[DONE] Total CDC events emitted to PostgreSQL: {events_generated}")


if __name__ == "__main__":
    main()
