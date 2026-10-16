# DataPulse — Source Schema and Relationship Analysis

Generated: 2026-10-16 15:06 UTC
Source directory: `data\raw`

This report is analysis-only. It does not alter source files, create database tables, or deduplicate records.

Null means an empty or whitespace-only CSV field. Candidate-key duplicate counts are repeated complete key values beyond their first occurrence. Referential-integrity counts include every source row; blank foreign keys are reported separately from orphans.

## Dataset schemas

### customers (`olist_customers_dataset.csv`)

- Rows: 99,441
- Columns: 5

| Column | Null values |
| --- | ---: |
| `customer_id` | 0 |
| `customer_unique_id` | 0 |
| `customer_zip_code_prefix` | 0 |
| `customer_city` | 0 |
| `customer_state` | 0 |

### geolocation (`olist_geolocation_dataset.csv`)

- Rows: 1,000,163
- Columns: 5

| Column | Null values |
| --- | ---: |
| `geolocation_zip_code_prefix` | 0 |
| `geolocation_lat` | 0 |
| `geolocation_lng` | 0 |
| `geolocation_city` | 0 |
| `geolocation_state` | 0 |

### order_items (`olist_order_items_dataset.csv`)

- Rows: 112,650
- Columns: 7

| Column | Null values |
| --- | ---: |
| `order_id` | 0 |
| `order_item_id` | 0 |
| `product_id` | 0 |
| `seller_id` | 0 |
| `shipping_limit_date` | 0 |
| `price` | 0 |
| `freight_value` | 0 |

### order_payments (`olist_order_payments_dataset.csv`)

- Rows: 103,886
- Columns: 5

| Column | Null values |
| --- | ---: |
| `order_id` | 0 |
| `payment_sequential` | 0 |
| `payment_type` | 0 |
| `payment_installments` | 0 |
| `payment_value` | 0 |

### order_reviews (`olist_order_reviews_dataset.csv`)

- Rows: 99,224
- Columns: 7

| Column | Null values |
| --- | ---: |
| `review_id` | 0 |
| `order_id` | 0 |
| `review_score` | 0 |
| `review_comment_title` | 87,658 |
| `review_comment_message` | 58,274 |
| `review_creation_date` | 0 |
| `review_answer_timestamp` | 0 |

### orders (`olist_orders_dataset.csv`)

- Rows: 99,441
- Columns: 8

| Column | Null values |
| --- | ---: |
| `order_id` | 0 |
| `customer_id` | 0 |
| `order_status` | 0 |
| `order_purchase_timestamp` | 0 |
| `order_approved_at` | 160 |
| `order_delivered_carrier_date` | 1,783 |
| `order_delivered_customer_date` | 2,965 |
| `order_estimated_delivery_date` | 0 |

### products (`olist_products_dataset.csv`)

- Rows: 32,951
- Columns: 9

| Column | Null values |
| --- | ---: |
| `product_id` | 0 |
| `product_category_name` | 610 |
| `product_name_lenght` | 610 |
| `product_description_lenght` | 610 |
| `product_photos_qty` | 610 |
| `product_weight_g` | 2 |
| `product_length_cm` | 2 |
| `product_height_cm` | 2 |
| `product_width_cm` | 2 |

### sellers (`olist_sellers_dataset.csv`)

- Rows: 3,095
- Columns: 4

| Column | Null values |
| --- | ---: |
| `seller_id` | 0 |
| `seller_zip_code_prefix` | 0 |
| `seller_city` | 0 |
| `seller_state` | 0 |

### product_category_name_translation (`product_category_name_translation.csv`)

- Rows: 71
- Columns: 2

| Column | Null values |
| --- | ---: |
| `product_category_name` | 0 |
| `product_category_name_english` | 0 |

## Candidate-key analysis

| Dataset | Key fields | Null-key rows | Duplicate rows | Unique complete keys | Assessment |
| --- | --- | ---: | ---: | ---: | --- |
| `customers` | `customer_id` | 0 | 0 | 99,441 | Candidate |
| `geolocation` | `geolocation_zip_code_prefix` | 0 | 981,148 | 19,015 | Investigative only; not asserted as a key |
| `geolocation` | `geolocation_zip_code_prefix + geolocation_lat + geolocation_lng` | 0 | 280,015 | 720,148 | Investigative only; not asserted as a key |
| `geolocation` | `geolocation_zip_code_prefix + geolocation_lat + geolocation_lng + geolocation_city + geolocation_state` | 0 | 261,836 | 738,327 | Investigative only; not asserted as a key |
| `order_items` | `order_id + order_item_id` | 0 | 0 | 112,650 | Candidate |
| `order_payments` | `order_id + payment_sequential` | 0 | 0 | 103,886 | Candidate |
| `order_reviews` | `review_id` | 0 | 814 | 98,410 | Investigative only; not asserted as a key |
| `orders` | `order_id` | 0 | 0 | 99,441 | Candidate |
| `products` | `product_id` | 0 | 0 | 32,951 | Candidate |
| `sellers` | `seller_id` | 0 | 0 | 3,095 | Candidate |
| `product_category_name_translation` | `product_category_name` | 0 | 0 | 71 | Candidate |

Review `review_id` is measured for nulls and duplicates but is not assumed to be unique. Geolocation is investigated using ZIP prefix, ZIP prefix + latitude + longitude, and the complete row; ZIP prefix alone is not assumed to be unique.

## Referential-integrity analysis

| Relationship | Source rows | Null-key rows | Orphan rows |
| --- | ---: | ---: | ---: |
| `orders.customer_id` | 99,441 | 0 | 0 |
| `order_items.order_id` | 112,650 | 0 | 0 |
| `order_items.product_id` | 112,650 | 0 | 0 |
| `order_items.seller_id` | 112,650 | 0 | 0 |
| `order_payments.order_id` | 103,886 | 0 | 0 |
| `order_reviews.order_id` | 99,224 | 0 | 0 |
| `products.product_category_name` | 32,951 | 610 | 13 |
