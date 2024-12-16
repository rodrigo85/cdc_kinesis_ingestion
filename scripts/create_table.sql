CREATE TABLE delivery.orders (
	id serial4 NOT NULL,
	order_number varchar(50) NOT NULL,
	customer_name varchar(100) NOT NULL,
	status varchar(20) DEFAULT 'Pending'::character varying NULL,
	total_amount numeric(10, 2) NOT NULL,
	payment_status varchar(20) DEFAULT 'Pending'::character varying NULL,
	delivery_address text NULL,
	delivery_notes text NULL,
	created_at timestamp DEFAULT now() NULL,
	updated_at timestamp DEFAULT now() NULL,
	estimated_delivery_time timestamp NULL,
	driver_id int4 NULL,
	restaurant_id int4 NULL,
	CONSTRAINT orders_order_number_key UNIQUE (order_number),
	CONSTRAINT orders_pkey PRIMARY KEY (id)
);