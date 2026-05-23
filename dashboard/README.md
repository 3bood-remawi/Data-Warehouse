# Movie Rental Data Warehouse Dashboard

This is a simple Streamlit dashboard for demonstrating the Data Warehouse project.
It is not the main project; it is only a visualization layer that helps the instructor see what the ETL and DW produced.

## What it shows

- Total revenue
- Total rentals
- Total customers
- Total films
- Monthly revenue trend
- Top rented films
- Revenue by category
- Store performance
- Top customers by spending
- Late return analysis
- DW row-count validation
- ETL pipeline explanation
- Dimensional model explanation

## Why Streamlit?

Streamlit is simple and Python-based. It lets us show the analytical results without spending time on a full frontend framework like React.

## Before running

Make sure these steps are already done:

1. Import the OLTP Sakila database into MySQL.
2. Run the DW schema file from the repo:

```text
sql/create_dw_schema.sql
```

3. Run the ETL script so `movie_rental_dw` has data.

## Install requirements

From the project root:

```bash
pip install -r dashboard/requirements.txt
```

## Configure database connection

Create a `.env` file in the project root or inside the `dashboard` folder:

```text
DW_URI=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/movie_rental_dw
```

## Run

From the project root:

```bash
streamlit run dashboard/app.py
```

## Demo mode

If MySQL is not connected yet, the dashboard automatically supports demo data.
This is useful to check the UI, but for the final presentation, turn off demo mode and connect to the real `movie_rental_dw` database.

## Presentation sentence

Use this explanation:

> This dashboard is not the main project. It is a simple visualization layer that demonstrates how our ETL-loaded Data Warehouse answers analytical business questions.
