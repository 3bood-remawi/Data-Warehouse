# Project Update Guide

Add these two folders to the root of the GitHub project:

```text
Data-Warehouse/
│
├── sql/
│   └── create_dw_schema.sql
│
├── ETL/
│   ├── sakila_etl.py
│   ├── analytical_queries.sql
│   ├── validate_dw_counts.sql
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── dashboard/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── RUN_DASHBOARD_WINDOWS.bat
│   ├── RUN_DASHBOARD_MAC_LINUX.sh
│   └── README.md
│
├── report/
└── diagrams/
```

## Why this improves the project

The original report explains the dimensional model and ETL conceptually. These additions make it practical:

```text
Sakila OLTP dump
    ↓
ETL script
    ↓
movie_rental_dw schema
    ↓
analytical SQL queries
    ↓
Streamlit dashboard
```

## What to say to the instructor

> We added a small dashboard only as a demonstration layer. The main work is still the Data Warehouse design and ETL. The dashboard shows the analytical questions being answered after the OLTP data is transformed and loaded into the DW.

## Recommended presentation order

1. Show the OLTP source tables briefly.
2. Show the DW schema / dimensional model.
3. Explain the ETL loading order.
4. Run or show the ETL result counts.
5. Open the Streamlit dashboard.
6. Show business questions and charts.
7. Mention that the dashboard reads from the DW, not directly from OLTP.
