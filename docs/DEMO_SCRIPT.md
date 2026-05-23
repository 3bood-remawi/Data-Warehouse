# Short Demo Script

Use this script during the presentation.

## Opening

Our project starts from a normalized OLTP movie rental database. This type of database is good for daily operations, but it is not ideal for analytical questions. So we designed a Data Warehouse using fact and dimension tables.

## ETL Explanation

We used ETL to extract data from the OLTP tables, transform it into analytical form, and load it into the DW.

The most important transformations are:

- Joining normalized OLTP tables.
- Creating date keys.
- Mapping natural keys to surrogate dimension keys.
- Calculating rental duration.
- Detecting late returns.
- Loading dimensions before fact tables.

## Dashboard Explanation

The dashboard is not the main project. It is only a visualization layer that helps show the final result.

It answers questions like:

- What is the monthly revenue trend?
- Which films are rented the most?
- Which categories generate the highest revenue?
- Which store performs better?
- Who are the top customers?
- Which categories have more late returns?

## Final sentence

This proves that the Data Warehouse design supports analytical reporting better than querying the OLTP database directly.
