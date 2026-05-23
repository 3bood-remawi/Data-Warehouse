# Movie Rental Data Warehouse

> A complete high-level Data Warehouse design based on the Sakila OLTP Movie Rental schema — built for a Data Warehousing / Data Architecture course assignment.

----

## 📁 Repository Structure

```
movie-rental-data-warehouse/
│
├── README.md                              ← You are here
├── report/
│   └── Movie_Rental_DW_Report.md         ← Full written report (all 7 sections)
│
├── diagrams/
│   └── dimensional_model_diagram.png     ← using hybrid star/snowflake schema principles
│
└── sql/
    └── create_dw_schema.sql              ← Full DDL for the data warehouse
```

---

## 📌 Project Overview

This project transforms the **Sakila OLTP movie rental database** into a fully designed **dimensional data warehouse** using star schema principles. The goal is to enable analytical reporting on:

- 🎬 Film popularity & revenue
- 👥 Customer behaviour & segmentation
- 🏪 Store & staff performance
- 📅 Time-based trends (daily, monthly, quarterly, yearly)
- 🌍 Location-based activity analysis

---

## 🏗️ Dimensional Model Summary

### Fact Tables
| Fact Table | Grain | Key Measures |
|---|---|---|
| `fact_rental` | One row per rental transaction | rental_duration_days, is_late_return, days_overdue |
| `fact_payment` | One row per payment transaction | payment_amount |

### Dimension Tables
| Dimension | Source OLTP Tables | Purpose |
|---|---|---|
| `dim_date` | Generated | Time-based filtering and trending |
| `dim_customer` | customer, address, city, country | Customer analysis (SCD Type 2) |
| `dim_film` | film, language, film_category, category | Film attributes and classification |
| `dim_category` | category | Genre-level analysis |
| `dim_language` | language | Language-based filtering |
| `dim_actor` | actor | Actor-level analysis |
| `dim_store` | store, address, city, country | Store performance |
| `dim_staff` | staff, address | Staff attribution |
| `dim_location` | address, city, country | Shared geography dimension |

---

## 🚀 How to Use the SQL

1.  Open MySQL Workbench, 
2.  open the file sql
3.  create_dw_schema.sql
4.  then execute the full script.

The report explains the proposed ETL process conceptually. Full ETL population code is not required for this assignment.
---

## 📄 Report

The full written report is in [`report/Movie_Rental_DW_Report.md`](report/Movie_Rental_DW_Report.md). It covers:

1. Introduction
2. Business Questions
3. Dimensional Model Design (Fact & Dimension tables)
4. Dimensional Model Diagram
5. ETL Design (Extract → Transform → Load)
6. Data Quality Considerations
7. Conclusion

---

## 🛠️ Technologies

- **OLTP Source**: Sakila MySQL Database
- **DW Schema**: MySQL / MariaDB compatible SQL
- **Modeling Approach**: Star Schema with Snowflake extensions (bridge table for film-actor M:M)
- **SCD Strategy**: Type 2 on `dim_customer`

---

## 👩‍💻 Author

Data Warehousing Assignment — Movie Rental DW Design
