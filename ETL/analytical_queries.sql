-- Analytical Queries for Movie Rental Data Warehouse
-- Run after ETL is completed.

USE movie_rental_dw;

-- 1) Monthly revenue trend
SELECT
    d.year,
    d.month_number,
    d.month_name,
    SUM(fp.payment_amount) AS total_revenue,
    COUNT(*) AS payment_count
FROM fact_payment fp
JOIN dim_date d ON fp.payment_date_key = d.date_key
GROUP BY d.year, d.month_number, d.month_name
ORDER BY d.year, d.month_number;

-- 2) Top 10 films by rental count
SELECT
    f.title,
    f.category_name,
    COUNT(*) AS total_rentals
FROM fact_rental fr
JOIN dim_film f ON fr.film_key = f.film_key
GROUP BY f.title, f.category_name
ORDER BY total_rentals DESC
LIMIT 10;

-- 3) Top 10 films by revenue
SELECT
    f.title,
    f.category_name,
    SUM(fp.payment_amount) AS total_revenue
FROM fact_payment fp
JOIN dim_film f ON fp.film_key = f.film_key
GROUP BY f.title, f.category_name
ORDER BY total_revenue DESC
LIMIT 10;

-- 4) Revenue by category
SELECT
    f.category_name,
    SUM(fp.payment_amount) AS total_revenue,
    COUNT(*) AS payment_count
FROM fact_payment fp
JOIN dim_film f ON fp.film_key = f.film_key
GROUP BY f.category_name
ORDER BY total_revenue DESC;

-- 5) Store performance without fact-table fanout
WITH rental_summary AS (
    SELECT store_key, COUNT(*) AS total_rentals
    FROM fact_rental
    GROUP BY store_key
),
payment_summary AS (
    SELECT store_key, SUM(payment_amount) AS total_revenue, COUNT(*) AS total_payments
    FROM fact_payment
    GROUP BY store_key
)
SELECT
    s.store_id,
    l.city,
    l.country,
    COALESCE(r.total_rentals, 0) AS total_rentals,
    COALESCE(p.total_revenue, 0) AS total_revenue,
    COALESCE(p.total_payments, 0) AS total_payments
FROM dim_store s
JOIN dim_location l ON s.location_key = l.location_key
LEFT JOIN rental_summary r ON s.store_key = r.store_key
LEFT JOIN payment_summary p ON s.store_key = p.store_key
ORDER BY total_revenue DESC;

-- 6) Top customers by spending
SELECT
    c.customer_id,
    c.full_name,
    l.city,
    l.country,
    SUM(fp.payment_amount) AS total_spent,
    COUNT(*) AS payment_count
FROM fact_payment fp
JOIN dim_customer c ON fp.customer_key = c.customer_key
JOIN dim_location l ON c.location_key = l.location_key
GROUP BY c.customer_id, c.full_name, l.city, l.country
ORDER BY total_spent DESC
LIMIT 10;

-- 7) Staff performance by revenue
SELECT
    st.staff_id,
    st.full_name,
    s.store_id,
    SUM(fp.payment_amount) AS total_revenue,
    COUNT(*) AS handled_payments
FROM fact_payment fp
JOIN dim_staff st ON fp.staff_key = st.staff_key
JOIN dim_store s ON st.store_key = s.store_key
GROUP BY st.staff_id, st.full_name, s.store_id
ORDER BY total_revenue DESC;

-- 8) Late return analysis by category
SELECT
    f.category_name,
    COUNT(*) AS total_rentals,
    SUM(CASE WHEN fr.is_late_return = TRUE THEN 1 ELSE 0 END) AS late_returns,
    ROUND(SUM(CASE WHEN fr.is_late_return = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)
        AS late_return_percentage
FROM fact_rental fr
JOIN dim_film f ON fr.film_key = f.film_key
WHERE fr.return_date_actual IS NOT NULL
GROUP BY f.category_name
ORDER BY late_return_percentage DESC;
