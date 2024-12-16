INSERT INTO delivery.orders (
    order_number, customer_name, status, total_amount, payment_status, 
    delivery_address, delivery_notes, estimated_delivery_time, driver_id, 
    restaurant_id
) 
VALUES 
(
    '2156422', 
    'Jane Smith', 
    'Preparing', 
    30.75, 
    'Paid', 
    '456 Elm St, Springfield', 
    'Call on arrival', 
    NOW() + INTERVAL '45 minutes', 
    2, 
    3
),
(
    '2156423', 
    'Michael Johnson', 
    'Delivered', 
    89.20, 
    'Paid', 
    '789 Pine St, Springfield', 
    'Hand it to the customer', 
    NOW() - INTERVAL '15 minutes', 
    3, 
    1
),
(
    '2156424', 
    'Emily Davis', 
    'Pending', 
    22.90, 
    'Pending', 
    '321 Maple Ave, Springfield', 
    'Ring the doorbell', 
    NOW() + INTERVAL '20 minutes', 
    4, 
    5
),
(
    '2156425', 
    'David Martinez', 
    'Preparing', 
    65.40, 
    'Paid', 
    '654 Oak Rd, Springfield', 
    'Leave it with the concierge', 
    NOW() + INTERVAL '50 minutes', 
    1, 
    4
),
(
    '2156426', 
    'Sarah Wilson', 
    'Out for Delivery', 
    38.15, 
    'Paid', 
    '987 Birch Ln, Springfield', 
    'Do not knock, baby sleeping', 
    NOW() + INTERVAL '25 minutes', 
    2, 
    2
),
(
    '2156427', 
    'James Taylor', 
    'Delivered', 
    49.95, 
    'Paid', 
    '741 Cedar Blvd, Springfield', 
    'Call when outside', 
    NOW() - INTERVAL '10 minutes', 
    5, 
    3
),
(
    '2156428', 
    'Olivia Moore', 
    'Cancelled', 
    27.30, 
    'Refunded', 
    '258 Willow St, Springfield', 
    'Customer cancelled the order', 
    NOW() + INTERVAL '0 minutes', 
    NULL, 
    1
),
(
    '2156429', 
    'William White', 
    'Pending', 
    33.60, 
    'Pending', 
    '135 Spruce Dr, Springfield', 
    'Buzz apartment 5B', 
    NOW() + INTERVAL '40 minutes', 
    4, 
    2
),
(
    '2156430', 
    'Isabella Harris', 
    'Preparing', 
    56.80, 
    'Paid', 
    '673 Sycamore Pl, Springfield', 
    'Knock loudly', 
    NOW() + INTERVAL '55 minutes', 
    3, 
    4
);