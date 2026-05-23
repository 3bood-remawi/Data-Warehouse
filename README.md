# Data Warehouse Project Additions

This package contains two additions for the Movie Rental Data Warehouse project:

1. `ETL/` — Python ETL script and SQL validation/analysis queries.
2. `dashboard/` — Simple Streamlit dashboard for presenting the DW results.

These folders are designed to be copied into the root of the existing GitHub repository.

## Main idea

The goal is to show the complete pipeline:

```text
OLTP Database → ETL → Data Warehouse → Analytical Dashboard
```

## Run order

1. Import the Sakila OLTP dump into MySQL as `sakila`.
2. Run `sql/create_dw_schema.sql` from the original repo.
3. Configure `.env` with `OLTP_URI` and `DW_URI`.
4. Run `python ETL/sakila_etl.py`.
5. Run `streamlit run dashboard/app.py`.

## Important

The dashboard includes demo mode so you can preview the UI even before MySQL is connected. For the final presentation, connect it to the real `movie_rental_dw` database.
