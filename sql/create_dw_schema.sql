DROP DATABASE IF EXISTS movie_rental_dw;
CREATE DATABASE movie_rental_dw;
USE movie_rental_dw;

-- ============================================================
-- Movie Rental Data Warehouse Schema
-- Dimensional Model: Hybrid Star/Snowflake Schema
-- Source OLTP: Sakila Movie Rental Database
-- ============================================================

-- ============================================================
-- DROP TABLES
-- ============================================================

DROP TABLE IF EXISTS fact_payment;
DROP TABLE IF EXISTS fact_rental;
DROP TABLE IF EXISTS bridge_film_actor;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_film;
DROP TABLE IF EXISTS dim_category;
DROP TABLE IF EXISTS dim_language;
DROP TABLE IF EXISTS dim_actor;
DROP TABLE IF EXISTS dim_store;
DROP TABLE IF EXISTS dim_staff;
DROP TABLE IF EXISTS dim_location;

-- ============================================================
-- DIMENSION: dim_date
-- ============================================================

CREATE TABLE dim_date (
    date_key        INT             NOT NULL,
    full_date       DATE            NOT NULL,
    day_of_week     TINYINT         NOT NULL,
    day_name        VARCHAR(10)     NOT NULL,
    day_of_month    TINYINT         NOT NULL,
    day_of_year     SMALLINT        NOT NULL,
    week_of_year    TINYINT         NOT NULL,
    month_number    TINYINT         NOT NULL,
    month_name      VARCHAR(10)     NOT NULL,
    quarter         TINYINT         NOT NULL,
    year            SMALLINT        NOT NULL,
    is_weekend      BOOLEAN         NOT NULL,
    is_weekday      BOOLEAN         NOT NULL,
    fiscal_year     SMALLINT        NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key)
);

-- ============================================================
-- DIMENSION: dim_location
-- ============================================================

CREATE TABLE dim_location (
    location_key    INT             NOT NULL AUTO_INCREMENT,
    address         VARCHAR(50)     NOT NULL,
    address2        VARCHAR(50),
    district        VARCHAR(20),
    city            VARCHAR(50)     NOT NULL,
    country         VARCHAR(50)     NOT NULL,
    postal_code     VARCHAR(10),
    phone           VARCHAR(20),
    CONSTRAINT pk_dim_location PRIMARY KEY (location_key)
);

-- ============================================================
-- DIMENSION: dim_customer
-- ============================================================

CREATE TABLE dim_customer (
    customer_key        INT             NOT NULL AUTO_INCREMENT,
    customer_id         SMALLINT        NOT NULL,
    first_name          VARCHAR(45)     NOT NULL,
    last_name           VARCHAR(45)     NOT NULL,
    full_name           VARCHAR(91)     NOT NULL,
    email               VARCHAR(50),
    location_key        INT             NOT NULL,
    active              BOOLEAN         NOT NULL,
    eff_start_date      DATE            NOT NULL,
    eff_end_date        DATE,
    is_current          BOOLEAN         NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_dim_customer PRIMARY KEY (customer_key),
    CONSTRAINT fk_customer_location FOREIGN KEY (location_key)
        REFERENCES dim_location (location_key)
);

-- ============================================================
-- DIMENSION: dim_language
-- ============================================================

CREATE TABLE dim_language (
    language_key    INT             NOT NULL AUTO_INCREMENT,
    language_id     TINYINT         NOT NULL,
    language_name   VARCHAR(20)     NOT NULL,
    CONSTRAINT pk_dim_language PRIMARY KEY (language_key)
);

-- ============================================================
-- DIMENSION: dim_category
-- ============================================================

CREATE TABLE dim_category (
    category_key    INT             NOT NULL AUTO_INCREMENT,
    category_id     TINYINT         NOT NULL,
    category_name   VARCHAR(25)     NOT NULL,
    CONSTRAINT pk_dim_category PRIMARY KEY (category_key)
);

-- ============================================================
-- DIMENSION: dim_actor
-- ============================================================

CREATE TABLE dim_actor (
    actor_key       INT             NOT NULL AUTO_INCREMENT,
    actor_id        SMALLINT        NOT NULL,
    first_name      VARCHAR(45)     NOT NULL,
    last_name       VARCHAR(45)     NOT NULL,
    full_name       VARCHAR(91)     NOT NULL,
    CONSTRAINT pk_dim_actor PRIMARY KEY (actor_key)
);

-- ============================================================
-- DIMENSION: dim_film
-- ============================================================

CREATE TABLE dim_film (
    film_key              INT             NOT NULL AUTO_INCREMENT,
    film_id               SMALLINT        NOT NULL,
    title                 VARCHAR(128)    NOT NULL,
    description           TEXT,
    release_year          YEAR,
    language_key          INT             NOT NULL,
    original_language_key INT,
    rental_duration       TINYINT         NOT NULL,
    rental_rate           DECIMAL(4,2)    NOT NULL,
    length_minutes        SMALLINT,
    replacement_cost      DECIMAL(5,2)    NOT NULL,
    rating                VARCHAR(10),
    special_features      VARCHAR(255),
    category_key          INT             NOT NULL,
    category_name         VARCHAR(25)     NOT NULL,
    CONSTRAINT pk_dim_film PRIMARY KEY (film_key),
    CONSTRAINT fk_film_language FOREIGN KEY (language_key)
        REFERENCES dim_language (language_key),
    CONSTRAINT fk_film_category FOREIGN KEY (category_key)
        REFERENCES dim_category (category_key)
);

-- ============================================================
-- BRIDGE TABLE: bridge_film_actor
-- ============================================================

CREATE TABLE bridge_film_actor (
    film_key        INT     NOT NULL,
    actor_key       INT     NOT NULL,
    CONSTRAINT pk_bridge_film_actor PRIMARY KEY (film_key, actor_key),
    CONSTRAINT fk_bfa_film FOREIGN KEY (film_key)
        REFERENCES dim_film (film_key),
    CONSTRAINT fk_bfa_actor FOREIGN KEY (actor_key)
        REFERENCES dim_actor (actor_key)
);

-- ============================================================
-- DIMENSION: dim_store
-- ============================================================

CREATE TABLE dim_store (
    store_key       INT             NOT NULL AUTO_INCREMENT,
    store_id        TINYINT         NOT NULL,
    location_key    INT             NOT NULL,
    manager_name    VARCHAR(91),
    CONSTRAINT pk_dim_store PRIMARY KEY (store_key),
    CONSTRAINT fk_store_location FOREIGN KEY (location_key)
        REFERENCES dim_location (location_key)
);

-- ============================================================
-- DIMENSION: dim_staff
-- ============================================================

CREATE TABLE dim_staff (
    staff_key       INT             NOT NULL AUTO_INCREMENT,
    staff_id        TINYINT         NOT NULL,
    first_name      VARCHAR(45)     NOT NULL,
    last_name       VARCHAR(45)     NOT NULL,
    full_name       VARCHAR(91)     NOT NULL,
    email           VARCHAR(50),
    store_key       INT             NOT NULL,
    active          BOOLEAN         NOT NULL,
    CONSTRAINT pk_dim_staff PRIMARY KEY (staff_key),
    CONSTRAINT fk_staff_store FOREIGN KEY (store_key)
        REFERENCES dim_store (store_key)
);

-- ============================================================
-- FACT TABLE: fact_rental
-- ============================================================

CREATE TABLE fact_rental (
    rental_id               INT             NOT NULL,
    rental_date_key         INT             NOT NULL,
    return_date_key         INT,
    customer_key            INT             NOT NULL,
    film_key                INT             NOT NULL,
    store_key               INT             NOT NULL,
    staff_key               INT             NOT NULL,
    inventory_id            INT             NOT NULL,
    rental_duration_days    INT,
    expected_duration_days  TINYINT         NOT NULL,
    is_late_return          BOOLEAN,
    days_overdue            INT,
    rental_count            TINYINT         NOT NULL DEFAULT 1,
    rental_date_actual      DATETIME        NOT NULL,
    return_date_actual      DATETIME,
    CONSTRAINT pk_fact_rental PRIMARY KEY (rental_id),
    CONSTRAINT fk_fr_rental_date FOREIGN KEY (rental_date_key)
        REFERENCES dim_date (date_key),
    CONSTRAINT fk_fr_return_date FOREIGN KEY (return_date_key)
        REFERENCES dim_date (date_key),
    CONSTRAINT fk_fr_customer FOREIGN KEY (customer_key)
        REFERENCES dim_customer (customer_key),
    CONSTRAINT fk_fr_film FOREIGN KEY (film_key)
        REFERENCES dim_film (film_key),
    CONSTRAINT fk_fr_store FOREIGN KEY (store_key)
        REFERENCES dim_store (store_key),
    CONSTRAINT fk_fr_staff FOREIGN KEY (staff_key)
        REFERENCES dim_staff (staff_key)
);

-- ============================================================
-- FACT TABLE: fact_payment
-- ============================================================

CREATE TABLE fact_payment (
    payment_id          INT             NOT NULL,
    payment_date_key    INT             NOT NULL,
    customer_key        INT             NOT NULL,
    staff_key           INT             NOT NULL,
    store_key           INT             NOT NULL,
    rental_id           INT,
    film_key            INT             NOT NULL,
    payment_amount      DECIMAL(5,2)    NOT NULL,
    payment_count TINYINT NOT NULL DEFAULT 1,
    payment_date_actual DATETIME        NOT NULL,
    CONSTRAINT pk_fact_payment PRIMARY KEY (payment_id),
    CONSTRAINT fk_fp_payment_date FOREIGN KEY (payment_date_key)
        REFERENCES dim_date (date_key),
    CONSTRAINT fk_fp_customer FOREIGN KEY (customer_key)
        REFERENCES dim_customer (customer_key),
    CONSTRAINT fk_fp_staff FOREIGN KEY (staff_key)
        REFERENCES dim_staff (staff_key),
    CONSTRAINT fk_fp_store FOREIGN KEY (store_key)
        REFERENCES dim_store (store_key),
    CONSTRAINT fk_fp_film FOREIGN KEY (film_key)
        REFERENCES dim_film (film_key)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_fr_rental_date ON fact_rental (rental_date_key);
CREATE INDEX idx_fr_customer ON fact_rental (customer_key);
CREATE INDEX idx_fr_film ON fact_rental (film_key);
CREATE INDEX idx_fr_store ON fact_rental (store_key);
CREATE INDEX idx_fr_staff ON fact_rental (staff_key);
CREATE INDEX idx_fr_late ON fact_rental (is_late_return);

CREATE INDEX idx_fp_payment_date ON fact_payment (payment_date_key);
CREATE INDEX idx_fp_customer ON fact_payment (customer_key);
CREATE INDEX idx_fp_store ON fact_payment (store_key);
CREATE INDEX idx_fp_film ON fact_payment (film_key);

CREATE INDEX idx_dd_year_month ON dim_date (year, month_number);
CREATE INDEX idx_dd_quarter ON dim_date (year, quarter);

CREATE INDEX idx_dc_natural ON dim_customer (customer_id, is_current);

CREATE INDEX idx_df_category ON dim_film (category_key);
CREATE INDEX idx_df_language ON dim_film (language_key);

-- ============================================================
-- PROCEDURE: Generate Date Dimension
-- ============================================================

DELIMITER $$

CREATE PROCEDURE generate_date_dimension(start_date DATE, end_date DATE)
BEGIN
    DECLARE current_date_val DATE DEFAULT start_date;

    WHILE current_date_val <= end_date DO
        INSERT INTO dim_date (
            date_key,
            full_date,
            day_of_week,
            day_name,
            day_of_month,
            day_of_year,
            week_of_year,
            month_number,
            month_name,
            quarter,
            year,
            is_weekend,
            is_weekday,
            fiscal_year
        ) VALUES (
            CAST(DATE_FORMAT(current_date_val, '%Y%m%d') AS UNSIGNED),
            current_date_val,
            DAYOFWEEK(current_date_val),
            DAYNAME(current_date_val),
            DAYOFMONTH(current_date_val),
            DAYOFYEAR(current_date_val),
            WEEK(current_date_val, 3),
            MONTH(current_date_val),
            MONTHNAME(current_date_val),
            QUARTER(current_date_val),
            YEAR(current_date_val),
            CASE WHEN DAYOFWEEK(current_date_val) IN (1,7) THEN TRUE ELSE FALSE END,
            CASE WHEN DAYOFWEEK(current_date_val) NOT IN (1,7) THEN TRUE ELSE FALSE END,
            YEAR(current_date_val)
        );

        SET current_date_val = DATE_ADD(current_date_val, INTERVAL 1 DAY);
    END WHILE;
END $$

DELIMITER ;

-- ============================================================
-- POPULATE dim_date
-- ============================================================

CALL generate_date_dimension('2005-01-01', '2010-12-31');

-- ============================================================
-- CHECK RESULT
-- ============================================================

SHOW TABLES;

SELECT COUNT(*) AS total_dates
FROM dim_date;

