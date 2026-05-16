# Movie Rental Data Warehouse — Design Report

**Course:** Data Warehousing / Data Architecture  
**Topic:** From OLTP Schema to Dimensional Model and ETL Design  
**Source System:** Sakila Movie Rental OLTP Database

---

## Section 1: Introduction

### 1.1 Purpose

This report proposes a high-level data warehouse (DW) design for a movie rental business. The source system is an OLTP database (the Sakila schema) that supports daily operational activities — registering customers, managing film inventory, recording rentals, and processing payments. While this OLTP schema is well-suited for transaction processing, it is not optimized for analytical reporting or business intelligence.

The proposed data warehouse reorganizes this operational data into a dimensional model that allows business managers to analyze rental activity, revenue trends, customer behaviour, film popularity, store performance, and staff productivity.

### 1.2 OLTP vs. Data Warehouse

| Characteristic | OLTP (Sakila) | Data Warehouse (Proposed) |
|---|---|---|
| Purpose | Record daily transactions | Support analytical reporting |
| Schema style | Normalized (3NF) | Denormalized (Star/Snowflake) |
| Query type | Short, frequent reads/writes | Complex, long-running reads |
| Data scope | Current operational data | Historical data over years |
| Users | Clerks, application systems | Analysts, managers, BI tools |
| Update frequency | Real-time | Periodic batch ETL |
| Key design goal | Eliminate redundancy | Simplify queries, fast aggregation |

The Sakila OLTP schema contains 16 tables with many-to-many relationships, normalized address hierarchies, and operational fields that are unnecessary for analysis. The proposed DW consolidates these into 9 dimension tables, 1 bridge table, and 2 fact tables.

---

## Section 2: Business Questions

The data warehouse is designed to answer the following analytical questions, grouped by business domain:

### 2.1 Film Popularity & Performance
1. Which films are rented most frequently?
2. Which films generate the highest revenue?
3. Which film categories (genres) are most popular?
4. Which films are returned late most often?
5. What is the average rental duration per film or category?
6. Which film ratings (G, PG, R, etc.) are rented most frequently?

**Why important:** Helps procurement and marketing teams decide which films to stock more copies of and which categories to promote.

### 2.2 Customer Behaviour
7. Which customers rent the most films?
8. Which customers generate the highest revenue?
9. How frequently does each customer rent?
10. What are the most active customer cities and countries?
11. Which customers have the most late returns?

**Why important:** Enables customer segmentation, loyalty programs, and targeted marketing campaigns.

### 2.3 Store & Staff Performance
12. Which stores generate the highest number of rentals?
13. Which stores generate the highest revenue?
14. Which staff members process the most rentals or payments?
15. How does store performance differ by location?

**Why important:** Supports resource allocation decisions, store expansion, and staff performance reviews.

### 2.4 Revenue & Time Trends
16. How does rental activity change by day, week, month, and year?
17. How does revenue change by month, quarter, or year?
18. Which months or seasons have the highest rental demand?
19. What is the total revenue by film category over time?

**Why important:** Supports financial forecasting, budgeting, and seasonal inventory planning.



**Why important:** Guides procurement decisions and helps identify operational bottlenecks.

---

## Section 3: Dimensional Model Design

### 3.1 Selected Business Processes

Two core business processes drive the data warehouse design:

| # | Business Process | Description |
|---|---|---|
| 1 | **Film Rental** | A customer rents a film from a store, managed by a staff member |
| 2 | **Payment** | A customer makes a payment for one or more rentals |

These two processes map directly to the `rental` and `payment` tables in the OLTP schema and form the basis of the two fact tables.

---

### 3.2 Fact Tables

#### Fact Table 1: `fact_rental`

| Property | Detail |
|---|---|
| **Business Process** | Film rental transaction |
| **Grain** | One row per individual rental transaction |
| **Source OLTP Tables** | rental, inventory, film, customer, staff, store |

**Dimensions (Foreign Keys):**

| Column | References | Description |
|---|---|---|
| rental_date_key | dim_date | Date the film was rented |
| return_date_key | dim_date | Date the film was returned (NULL if unreturned) |
| customer_key | dim_customer | Who rented the film |
| film_key | dim_film | Which film was rented |
| store_key | dim_store | From which store |
| staff_key | dim_staff | Processed by which staff member |

**Measures:**

| Measure | Type | Description |
|---|---|---|
| rental_duration_days | INT | Actual number of days the film was kept |
| expected_duration_days | TINYINT | Standard rental period for the film |
| is_late_return | BOOLEAN | Whether the film was returned late |
| days_overdue | INT | How many days past the expected return date |
| rental_count | TINYINT (=1) | Always 1; useful for COUNT aggregations |

**Degenerate Dimensions:** `rental_id`, `rental_date_actual`, `return_date_actual`

---

#### Fact Table 2: `fact_payment`

| Property | Detail |
|---|---|
| **Business Process** | Payment for rental |
| **Grain** | One row per individual payment transaction |
| **Source OLTP Tables** | payment, rental, inventory, film |

**Dimensions (Foreign Keys):**

| Column | References | Description |
|---|---|---|
| payment_date_key | dim_date | Date payment was made |
| customer_key | dim_customer | Who made the payment |
| staff_key | dim_staff | Which staff member processed it |
| store_key | dim_store | Which store processed it |
| film_key | dim_film | Film associated with the payment |

**Measures:**

| Measure | Type | Description |
|---|---|---|
| payment_amount | DECIMAL(5,2) | Amount paid |
| payment_count | TINYINT (=1) | Always 1; useful for COUNT aggregations |

**Degenerate Dimensions:** `payment_id`, `rental_id` (links back to fact_rental), `payment_date_actual`

---

### 3.3 Dimension Tables

#### dim_date
| Attribute | Description |
|---|---|
| date_key (PK) | Surrogate key: YYYYMMDD integer |
| full_date | Calendar date |
| day_of_week, day_name | 1–7 and name |
| day_of_month, day_of_year | Calendar position |
| week_of_year | ISO week number |
| month_number, month_name | 1–12 and name |
| quarter | 1–4 |
| year | Calendar year |
| is_weekend, is_weekday | Boolean flags |
| fiscal_year | Financial year |

**Source:** Generated by stored procedure (no OLTP source)  
**Purpose:** All time-based filtering and trend analysis across both fact tables

---

#### dim_customer
| Attribute | Description |
|---|---|
| customer_key (PK) | Surrogate key |
| customer_id | OLTP natural key |
| first_name, last_name, full_name | Customer name |
| email | Contact email |
| location_key (FK) | Links to dim_location |
| active | Active status |
| eff_start_date, eff_end_date, is_current | SCD Type 2 fields |

**Source OLTP:** customer, address, city, country  
**Purpose:** Customer segmentation, behaviour, and geographic analysis  
**SCD Strategy:** Type 2 — preserves history if customer address or status changes

---

#### dim_film
| Attribute | Description |
|---|---|
| film_key (PK) | Surrogate key |
| film_id | OLTP natural key |
| title, description | Film info |
| release_year | Year released |
| language_key (FK) | Links to dim_language |
| rental_duration | Expected rental days |
| rental_rate | Daily rental cost |
| length_minutes | Film length |
| replacement_cost | Cost if lost |
| rating | MPAA rating |
| special_features | DVD features |
| category_key (FK), category_name | Denormalized primary category |

**Source OLTP:** film, language, film_category, category  
**Purpose:** Film-level analysis of popularity, revenue, and late returns

---

#### dim_category
| Attribute | Description |
|---|---|
| category_key (PK) | Surrogate key |
| category_id | OLTP natural key |
| category_name | Genre name |

**Source OLTP:** category  
**Purpose:** Genre-level rollup analysis

---

#### dim_language
| Attribute | Description |
|---|---|
| language_key (PK) | Surrogate key |
| language_id | OLTP natural key |
| language_name | Language name |

**Source OLTP:** language  
**Purpose:** Film language filtering

---

#### dim_actor
| Attribute | Description |
|---|---|
| actor_key (PK) | Surrogate key |
| actor_id | OLTP natural key |
| first_name, last_name, full_name | Actor name |

**Source OLTP:** actor  
**Purpose:** Actor-level popularity analysis  
**Note:** Linked to dim_film via `bridge_film_actor` (many-to-many bridge table)

---

#### dim_store
| Attribute | Description |
|---|---|
| store_key (PK) | Surrogate key |
| store_id | OLTP natural key |
| location_key (FK) | Links to dim_location |
| manager_name | Denormalized from staff |

**Source OLTP:** store, address, city, country, staff  
**Purpose:** Store performance and location analysis

---

#### dim_staff
| Attribute | Description |
|---|---|
| staff_key (PK) | Surrogate key |
| staff_id | OLTP natural key |
| first_name, last_name, full_name | Staff name |
| email | Contact email |
| store_key (FK) | Links to dim_store |
| active | Employment status |

**Source OLTP:** staff, address  
**Purpose:** Staff performance tracking

---

#### dim_location
| Attribute | Description |
|---|---|
| location_key (PK) | Surrogate key |
| address, address2, district | Street address |
| city | City name |
| country | Country name |
| postal_code, phone | Contact info |

**Source OLTP:** address, city, country  
**Purpose:** Shared geography dimension used by both dim_customer and dim_store

---

#### bridge_film_actor
Resolves the many-to-many relationship between films and actors.

| Column | Description |
|---|---|
| film_key (PK, FK) | References dim_film |
| actor_key (PK, FK) | References dim_actor |

**Source OLTP:** film_actor  
**Usage:** JOIN bridge_film_actor to get all actors in a given film or all films for a given actor

---

### 3.4 Schema Type Decision

The proposed model is a **hybrid schema**:
- **Star schema core**: fact_rental and fact_payment connect directly to all major dimensions (date, customer, film, store, staff)
- **Snowflake extension**: dim_customer and dim_store reference dim_location rather than embedding address fields directly (avoids massive duplication of city/country data)
- **Bridge table**: bridge_film_actor handles the film-actor many-to-many relationship

This approach balances **query simplicity** (fewer joins for most reports) with **data integrity** (no redundant address storage).

### 3.5 Shared Dimensions

| Dimension | Shared by |
|---|---|
| dim_date | fact_rental (×2: rental_date, return_date), fact_payment |
| dim_customer | fact_rental, fact_payment |
| dim_film | fact_rental, fact_payment |
| dim_store | fact_rental, fact_payment |
| dim_staff | fact_rental, fact_payment |
| dim_location | dim_customer, dim_store |

Shared (conformed) dimensions allow **drill-across queries** — for example, comparing rental counts and payment revenue for the same customer, store, or film.

---

## Section 4: Dimensional Model Diagram

```
                              dim_date
                           ┌──────────────┐
                           │ date_key (PK)│
                           │ full_date    │
                           │ day_name     │
                           │ month_name   │
                           │ quarter      │
                           │ year         │
                           └──────┬───────┘
                                  │ rental_date_key
                                  │ return_date_key
   dim_customer                   │                        dim_film
 ┌────────────────┐               │                    ┌──────────────────┐
 │customer_key(PK)│───────────────┤                    │ film_key (PK)    │
 │customer_id     │               │                    │ film_id          │
 │full_name       │         ┌─────▼──────────┐         │ title            │
 │email           │         │  fact_rental   │─────────│ rental_duration  │
 │location_key(FK)│◄────────│────────────────│         │ rental_rate      │
 │active          │         │ rental_id (PK) │         │ rating           │
 │eff_start_date  │         │ rental_date_key│─────────│ category_key(FK) │
 │eff_end_date    │         │ return_date_key│         │ language_key(FK) │
 └────────────────┘         │ customer_key  │         └────────┬─────────┘
                            │ film_key      │                  │
   dim_location             │ store_key     │           dim_category
 ┌────────────────┐         │ staff_key     │         ┌────────────────┐
 │location_key(PK)│         │─── Measures ─│         │category_key(PK)│
 │address         │         │ duration_days │         │category_name   │
 │city            │         │ is_late       │         └────────────────┘
 │country         │         │ days_overdue  │
 └────────────────┘         └──────┬────────┘          dim_language
        ▲                          │                  ┌────────────────┐
        │                          │                  │language_key(PK)│
   dim_store             ┌─────────┴──────────┐       │language_name   │
 ┌────────────────┐      │   fact_payment     │       └────────────────┘
 │store_key (PK)  │◄─────│────────────────────│
 │store_id        │      │ payment_id (PK)    │
 │location_key(FK)│      │ payment_date_key   │──────► dim_date
 │manager_name    │      │ customer_key       │──────► dim_customer
 └────────────────┘      │ staff_key          │
                         │ store_key          │──────► dim_store
   dim_staff             │ film_key           │──────► dim_film
 ┌────────────────┐      │ rental_id (Deg.)   │──────► fact_rental
 │staff_key (PK)  │◄─────│── Measures ────────│
 │full_name       │      │ payment_amount     │
 │store_key (FK)  │      │ payment_count      │
 │active          │      └────────────────────┘
 └────────────────┘    bridge_film_actor        dim_actor
                     ┌──────────────────┐    ┌────────────────┐
                     │film_key (PK,FK)  │────│actor_key (PK)  │
                     │actor_key (PK,FK) │    │full_name       │
                     └──────────────────┘    └────────────────┘
```

---

## Section 5: ETL Design

### 5.1 Extract

The following OLTP tables are extracted as the source data for the data warehouse:

| OLTP Table | Why Extracted |
|---|---|
| `rental` | Core fact — every rental transaction |
| `payment` | Core fact — every payment transaction |
| `customer` | Customer dimension attributes |
| `inventory` | Links rental→film and rental→store |
| `film` | Film dimension attributes |
| `film_category` | Maps films to genres (M:M) |
| `film_actor` | Maps films to actors (M:M) |
| `category` | Genre names |
| `actor` | Actor names |
| `language` | Language names |
| `store` | Store dimension attributes |
| `staff` | Staff dimension attributes |
| `address` | Address for customers, stores, staff |
| `city` | City lookup (part of address hierarchy) |
| `country` | Country lookup (part of address hierarchy) |

**Extraction Strategy:**
- **Initial Load:** Full extract of all tables for historical data population
- **Incremental Load:** Use `last_update` timestamps (present on most Sakila tables) to extract only changed/new records since the last ETL run
- **Change Detection:** Compare OLTP `last_update` with a high-water-mark table stored in the DW staging area

---

### 5.2 Transform

Transformations are organized by destination table:

#### dim_date
- Generated entirely in ETL — no OLTP source needed
- A stored procedure loops through each day from 2005-01-01 to the current date
- Derives all calendar attributes (day name, week, quarter, etc.) using date functions

#### dim_location
- **Join:** `address` ← `city` ← `country` using address_id, city_id, country_id
- **Standardize:** Trim and title-case city and country names
- **Clean:** Replace NULL address2 with empty string
- **Deduplication:** Check for existing address records before inserting

#### dim_customer
- **Join:** `customer` ← `address` ← `city` ← `country`
- **Derive:** `full_name = CONCAT(first_name, ' ', last_name)`
- **Surrogate key:** Generate new customer_key via auto-increment
- **SCD Type 2:** If email or address changes, close old record (set eff_end_date, is_current=FALSE) and insert new record
- **Map:** Assign location_key from dim_location lookup

#### dim_language
- Direct load from `language` table
- Map language_id → surrogate language_key

#### dim_category
- Direct load from `category` table
- Map category_id → surrogate category_key

#### dim_actor
- Load from `actor` table
- **Derive:** `full_name = CONCAT(first_name, ' ', last_name)`
- Map actor_id → surrogate actor_key

#### dim_film
- **Join:** `film` ← `language` ← `film_category` ← `category`
- **Handle M:M:** Since a film can have multiple categories, select the primary (or first alphabetically) category for dim_film; full M:M is preserved in bridge table
- **Map:** language_id → language_key, category_id → category_key
- **Derive film_key:** surrogate auto-increment

#### bridge_film_actor
- **Join:** `film_actor` — look up film_key from dim_film, actor_key from dim_actor
- Insert one row per film-actor combination

#### dim_store
- **Join:** `store` ← `address` ← `city` ← `country`
- **Denormalize:** Look up manager's full name from `staff` WHERE staff_id = store.manager_staff_id
- **Map:** location_key from dim_location

#### dim_staff
- **Join:** `staff` ← `address` ← `city` ← `country`
- **Derive:** `full_name = CONCAT(first_name, ' ', last_name)`
- **Map:** store_key from dim_store

#### fact_rental
- **Source:** `rental` joined to `inventory` joined to `film`
- **Key resolution:**
  - rental_date → date_key lookup in dim_date
  - return_date → date_key lookup in dim_date (NULL if not returned)
  - customer_id → customer_key lookup in dim_customer (current record)
  - inventory.film_id → film_key lookup in dim_film
  - inventory.store_id → store_key lookup in dim_store
  - staff_id → staff_key lookup in dim_staff
- **Calculations:**
  - `rental_duration_days = DATEDIFF(return_date, rental_date)` (NULL if unreturned)
  - `expected_duration_days` = film.rental_duration
  - `is_late_return = rental_duration_days > expected_duration_days`
  - `days_overdue = MAX(0, rental_duration_days - expected_duration_days)`
- **Handle missing return dates:** Set return_date_key = NULL, is_late_return = NULL, rental_duration_days = NULL

#### fact_payment
- **Source:** `payment` joined to `rental` joined to `inventory`
- **Key resolution:** Similar to fact_rental
- **Validate:** Every payment must have a matching rental_id in fact_rental
- **Degenerate dimensions:** Keep payment_id and rental_id as reference columns

---

### 5.3 Load

#### Loading Order (dependency-driven)

```
1. dim_date          ← No dependencies
2. dim_location      ← No dependencies
3. dim_language      ← No dependencies
4. dim_category      ← No dependencies
5. dim_actor         ← No dependencies
6. dim_customer      ← Depends on dim_location
7. dim_film          ← Depends on dim_language, dim_category
8. bridge_film_actor ← Depends on dim_film, dim_actor
9. dim_store         ← Depends on dim_location
10. dim_staff        ← Depends on dim_store
11. fact_rental      ← Depends on all dimensions
12. fact_payment     ← Depends on all dimensions
```

**Why dimensions first:** Fact tables reference dimension surrogate keys via foreign keys. If dimension rows don't exist yet, the fact table inserts will fail referential integrity checks.

#### Surrogate Key Generation
- All dimension surrogate keys use `AUTO_INCREMENT` in MySQL
- The ETL process maintains a mapping table (`stg_key_map`) that records `(oltp_natural_key → dw_surrogate_key)` for each dimension, used for fast lookup during fact table population

#### Insert Strategies
- **New records:** `INSERT INTO dim_xxx VALUES (...)` using `INSERT IGNORE` or `ON DUPLICATE KEY UPDATE` to handle re-runs safely
- **Changed records (SCD Type 2):** 
  - Detect change by comparing current OLTP value with DW current record
  - `UPDATE dim_customer SET eff_end_date = TODAY, is_current = FALSE WHERE customer_id = X AND is_current = TRUE`
  - `INSERT new row with eff_start_date = TODAY, is_current = TRUE`
- **Fact tables:** Always INSERT — facts are immutable. Use `INSERT IGNORE` to prevent duplicates on re-runs
- **Late-arriving data:** If a return_date arrives after the ETL run, UPDATE the existing fact_rental row's return-related measures

#### Staging Area
All extracted OLTP data is first loaded into a **staging schema** (`stg_*` tables) before transformation and final DW loading. This allows:
- Validation before commitment
- Easy rollback if errors occur
- Separation of extraction and loading concerns

---

## Section 6: Data Quality Considerations

The following data quality rules are enforced during ETL:

| # | Rule | Check | Action on Failure |
|---|---|---|---|
| DQ-01 | **Not-null rental dates** | `rental_date IS NOT NULL` | Reject record, log to error table |
| DQ-02 | **Valid return dates** | `return_date IS NULL OR return_date >= rental_date` | Set return_date = NULL, flag record |
| DQ-03 | **Payment amount positive** | `payment_amount > 0` | Reject record, alert ETL team |
| DQ-04 | **Valid customer reference** | customer_id exists in dim_customer | Reject fact row, log orphan |
| DQ-05 | **Valid film reference** | film_id exists in dim_film | Reject fact row, log orphan |
| DQ-06 | **Rental rate positive** | `rental_rate > 0` | Flag film record for review |
| DQ-07 | **No duplicate payments** | payment_id unique in fact_payment | Skip duplicate, log warning |
| DQ-08 | **No duplicate rentals** | rental_id unique in fact_rental | Skip duplicate, log warning |
| DQ-09 | **Email format valid** | Email matches regex pattern | Load record but set email = NULL |
| DQ-10 | **Category exists for film** | Every film has at least one category | Assign 'Uncategorized', flag |

A **reconciliation report** is generated after each ETL run comparing:
- Row counts in OLTP source vs. DW fact tables
- Total payment_amount in OLTP `payment` vs. `fact_payment`
- Total rental count in OLTP `rental` vs. `fact_rental`

---

## Section 7: Conclusion

This report has presented a complete high-level data warehouse design for a movie rental business, transforming the operational Sakila OLTP database into an analytical dimensional model.

### Key Design Decisions

1. **Two fact tables** were chosen — `fact_rental` and `fact_payment` — because they represent the two distinct, measurable business processes (renting and paying), each with different grains and measures.

2. **Conformed dimensions** (dim_date, dim_customer, dim_film, dim_store, dim_staff) are shared between both fact tables, enabling drill-across analysis and consistent reporting across different subject areas.

3. **SCD Type 2** was applied to `dim_customer` to preserve the history of customer address and status changes, ensuring that historical rental and payment facts are always associated with the correct customer attributes at the time of the transaction.

4. **A bridge table** (`bridge_film_actor`) was used to correctly handle the many-to-many relationship between films and actors without distorting fact table metrics.

5. **dim_location** was created as a separate shared geography dimension, referenced by both `dim_customer` and `dim_store`, reducing address data redundancy while still enabling location-based analysis.

6. **Hybrid schema** (predominantly star with minor snowflake extensions) was chosen to balance query performance with data integrity.

### Business Value

The proposed data warehouse enables business managers to:
- Identify top-performing films, stores, and staff members
- Track revenue trends and plan inventory accordingly
- Analyze customer rental behaviour for targeted marketing
- Monitor late returns and operational efficiency
- Compare store performance across different cities and countries
- Make data-driven decisions based on historical trends rather than just current operational data

The ETL design ensures data is extracted reliably from the OLTP system, transformed cleanly into the dimensional format, and loaded with data quality checks that maintain the accuracy and trustworthiness of the warehouse.
