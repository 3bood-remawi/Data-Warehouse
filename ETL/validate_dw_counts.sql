-- Validation Checks for Movie Rental Data Warehouse

USE movie_rental_dw;

-- 1) Row counts for all DW tables
SELECT 'dim_date' AS table_name, COUNT(*) AS row_count FROM dim_date
UNION ALL SELECT 'dim_location', COUNT(*) FROM dim_location
UNION ALL SELECT 'dim_language', COUNT(*) FROM dim_language
UNION ALL SELECT 'dim_category', COUNT(*) FROM dim_category
UNION ALL SELECT 'dim_actor', COUNT(*) FROM dim_actor
UNION ALL SELECT 'dim_film', COUNT(*) FROM dim_film
UNION ALL SELECT 'bridge_film_actor', COUNT(*) FROM bridge_film_actor
UNION ALL SELECT 'dim_store', COUNT(*) FROM dim_store
UNION ALL SELECT 'dim_staff', COUNT(*) FROM dim_staff
UNION ALL SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL SELECT 'fact_rental', COUNT(*) FROM fact_rental
UNION ALL SELECT 'fact_payment', COUNT(*) FROM fact_payment;

-- 2) Rental fact foreign-key checks
SELECT
    SUM(CASE WHEN dc.customer_key IS NULL THEN 1 ELSE 0 END) AS missing_customers,
    SUM(CASE WHEN df.film_key IS NULL THEN 1 ELSE 0 END) AS missing_films,
    SUM(CASE WHEN ds.store_key IS NULL THEN 1 ELSE 0 END) AS missing_stores,
    SUM(CASE WHEN dst.staff_key IS NULL THEN 1 ELSE 0 END) AS missing_staff,
    SUM(CASE WHEN dd.date_key IS NULL THEN 1 ELSE 0 END) AS missing_rental_dates
FROM fact_rental fr
LEFT JOIN dim_customer dc ON fr.customer_key = dc.customer_key
LEFT JOIN dim_film df ON fr.film_key = df.film_key
LEFT JOIN dim_store ds ON fr.store_key = ds.store_key
LEFT JOIN dim_staff dst ON fr.staff_key = dst.staff_key
LEFT JOIN dim_date dd ON fr.rental_date_key = dd.date_key;

-- 3) Payment fact foreign-key checks
SELECT
    SUM(CASE WHEN dc.customer_key IS NULL THEN 1 ELSE 0 END) AS missing_customers,
    SUM(CASE WHEN df.film_key IS NULL THEN 1 ELSE 0 END) AS missing_films,
    SUM(CASE WHEN ds.store_key IS NULL THEN 1 ELSE 0 END) AS missing_stores,
    SUM(CASE WHEN dst.staff_key IS NULL THEN 1 ELSE 0 END) AS missing_staff,
    SUM(CASE WHEN dd.date_key IS NULL THEN 1 ELSE 0 END) AS missing_payment_dates
FROM fact_payment fp
LEFT JOIN dim_customer dc ON fp.customer_key = dc.customer_key
LEFT JOIN dim_film df ON fp.film_key = df.film_key
LEFT JOIN dim_store ds ON fp.store_key = ds.store_key
LEFT JOIN dim_staff dst ON fp.staff_key = dst.staff_key
LEFT JOIN dim_date dd ON fp.payment_date_key = dd.date_key;
