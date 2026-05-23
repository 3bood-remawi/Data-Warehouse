"""
Sakila OLTP -> Movie Rental Data Warehouse ETL

This script populates the GitHub DW schema `movie_rental_dw` from the Sakila OLTP database.
It follows the instructor pattern: Extract with SQL, Transform with Pandas, Load with SQLAlchemy.

Run:
    python ETL/sakila_etl.py
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


load_dotenv()
load_dotenv(Path(__file__).resolve().parent / ".env")

OLTP_URI = os.getenv("OLTP_URI", "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/sakila")
DW_URI = os.getenv("DW_URI", "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/movie_rental_dw")

TRUNCATE_ORDER = [
    "fact_payment",
    "fact_rental",
    "bridge_film_actor",
    "dim_customer",
    "dim_staff",
    "dim_store",
    "dim_film",
    "dim_actor",
    "dim_category",
    "dim_language",
    "dim_location",
]


def engine(uri: str) -> Engine:
    return create_engine(uri, pool_pre_ping=True)


def read_sql(db: Engine, query: str) -> pd.DataFrame:
    return pd.read_sql(text(query), con=db)


def mysql_ready(df: pd.DataFrame) -> pd.DataFrame:
    return df.astype(object).where(pd.notnull(df), None)


def load_table(dw: Engine, table: str, df: pd.DataFrame) -> None:
    if df.empty:
        print(f"[WARN] {table}: no rows to load")
        return
    mysql_ready(df).to_sql(table, con=dw, if_exists="append", index=False, chunksize=1000, method="multi")
    print(f"[LOAD] {table}: {len(df):,} rows")


def truncate_dw(dw: Engine) -> None:
    print("[RESET] Removing old DW rows to avoid duplicates...")
    with dw.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in TRUNCATE_ORDER:
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    print("[RESET] Done")


def make_location_nk(df: pd.DataFrame) -> pd.Series:
    cols = ["address", "address2", "district", "city", "country", "postal_code", "phone"]
    return df[cols].fillna("").astype(str).agg("|".join, axis=1)


def load_dim_location(oltp: Engine, dw: Engine) -> pd.DataFrame:
    src = read_sql(
        oltp,
        """
        SELECT
            a.address_id,
            a.address,
            NULLIF(a.address2, '') AS address2,
            NULLIF(a.district, '') AS district,
            c.city,
            co.country,
            NULLIF(a.postal_code, '') AS postal_code,
            NULLIF(a.phone, '') AS phone
        FROM address a
        JOIN city c ON a.city_id = c.city_id
        JOIN country co ON c.country_id = co.country_id
        ORDER BY a.address_id
        """,
    )
    src["location_nk"] = make_location_nk(src)
    load_cols = ["address", "address2", "district", "city", "country", "postal_code", "phone"]
    load_table(dw, "dim_location", src[load_cols])

    loaded = read_sql(dw, "SELECT location_key, address, address2, district, city, country, postal_code, phone FROM dim_location")
    loaded["location_nk"] = make_location_nk(loaded)
    mapping = src[["address_id", "location_nk"]].merge(loaded[["location_key", "location_nk"]], on="location_nk", how="left")
    if mapping["location_key"].isna().any():
        raise RuntimeError("Some locations were not mapped correctly.")
    return mapping[["address_id", "location_key"]]


def load_dim_language(oltp: Engine, dw: Engine) -> pd.DataFrame:
    df = read_sql(oltp, "SELECT language_id, TRIM(name) AS language_name FROM language ORDER BY language_id")
    load_table(dw, "dim_language", df)
    return read_sql(dw, "SELECT language_id, language_key FROM dim_language")


def load_dim_category(oltp: Engine, dw: Engine) -> pd.DataFrame:
    df = read_sql(oltp, "SELECT category_id, name AS category_name FROM category ORDER BY category_id")
    load_table(dw, "dim_category", df)
    return read_sql(dw, "SELECT category_id, category_key, category_name FROM dim_category")


def load_dim_actor(oltp: Engine, dw: Engine) -> pd.DataFrame:
    df = read_sql(
        oltp,
        """
        SELECT actor_id, first_name, last_name, CONCAT(first_name, ' ', last_name) AS full_name
        FROM actor
        ORDER BY actor_id
        """,
    )
    load_table(dw, "dim_actor", df)
    return read_sql(dw, "SELECT actor_id, actor_key FROM dim_actor")


def load_dim_film(oltp: Engine, dw: Engine, language_map: pd.DataFrame, category_map: pd.DataFrame) -> pd.DataFrame:
    src = read_sql(
        oltp,
        """
        SELECT
            f.film_id,
            f.title,
            f.description,
            f.release_year,
            f.language_id,
            f.original_language_id,
            f.rental_duration,
            f.rental_rate,
            f.length AS length_minutes,
            f.replacement_cost,
            f.rating,
            f.special_features,
            fc.category_id,
            c.name AS category_name
        FROM film f
        LEFT JOIN film_category fc ON f.film_id = fc.film_id
        LEFT JOIN category c ON fc.category_id = c.category_id
        ORDER BY f.film_id
        """,
    )
    df = src.merge(language_map, on="language_id", how="left")

    # In Sakila, original_language_id is usually NULL.
    # Pandas may read it as object, while language_map uses integer IDs.
    # Convert both sides to the same nullable integer type before merging.
    df["original_language_id"] = pd.to_numeric(
        df["original_language_id"],
        errors="coerce"
    ).astype("Int64")

    original_lang = language_map.rename(
        columns={
            "language_id": "original_language_id",
            "language_key": "original_language_key",
        }
    ).copy()
    original_lang["original_language_id"] = original_lang["original_language_id"].astype("Int64")

    df = df.merge(original_lang, on="original_language_id", how="left")
    df = df.merge(category_map, on=["category_id", "category_name"], how="left")

    required = ["language_key", "category_key"]
    if df[required].isna().any().any():
        raise RuntimeError("Some films could not be mapped to language/category dimensions.")

    load_cols = [
        "film_id",
        "title",
        "description",
        "release_year",
        "language_key",
        "original_language_key",
        "rental_duration",
        "rental_rate",
        "length_minutes",
        "replacement_cost",
        "rating",
        "special_features",
        "category_key",
        "category_name",
    ]
    load_table(dw, "dim_film", df[load_cols])
    return read_sql(dw, "SELECT film_id, film_key FROM dim_film")


def load_bridge_film_actor(oltp: Engine, dw: Engine, film_map: pd.DataFrame, actor_map: pd.DataFrame) -> None:
    src = read_sql(oltp, "SELECT film_id, actor_id FROM film_actor ORDER BY film_id, actor_id")
    df = src.merge(film_map, on="film_id", how="left").merge(actor_map, on="actor_id", how="left")
    if df[["film_key", "actor_key"]].isna().any().any():
        raise RuntimeError("Some bridge rows could not be mapped.")
    load_table(dw, "bridge_film_actor", df[["film_key", "actor_key"]].drop_duplicates())


def load_dim_store(oltp: Engine, dw: Engine, location_map: pd.DataFrame) -> pd.DataFrame:
    src = read_sql(
        oltp,
        """
        SELECT
            s.store_id,
            s.address_id,
            CONCAT(st.first_name, ' ', st.last_name) AS manager_name
        FROM store s
        LEFT JOIN staff st ON s.manager_staff_id = st.staff_id
        ORDER BY s.store_id
        """,
    )
    df = src.merge(location_map, on="address_id", how="left")
    if df["location_key"].isna().any():
        raise RuntimeError("Some stores could not be mapped to locations.")
    load_table(dw, "dim_store", df[["store_id", "location_key", "manager_name"]])
    return read_sql(dw, "SELECT store_id, store_key FROM dim_store")


def load_dim_staff(oltp: Engine, dw: Engine, store_map: pd.DataFrame) -> pd.DataFrame:
    src = read_sql(
        oltp,
        """
        SELECT
            staff_id,
            first_name,
            last_name,
            CONCAT(first_name, ' ', last_name) AS full_name,
            email,
            store_id,
            active
        FROM staff
        ORDER BY staff_id
        """,
    )
    df = src.merge(store_map, on="store_id", how="left")
    if df["store_key"].isna().any():
        raise RuntimeError("Some staff rows could not be mapped to stores.")
    load_cols = ["staff_id", "first_name", "last_name", "full_name", "email", "store_key", "active"]
    load_table(dw, "dim_staff", df[load_cols])
    return read_sql(dw, "SELECT staff_id, staff_key FROM dim_staff")


def load_dim_customer(oltp: Engine, dw: Engine, location_map: pd.DataFrame) -> pd.DataFrame:
    src = read_sql(
        oltp,
        """
        SELECT
            customer_id,
            first_name,
            last_name,
            CONCAT(first_name, ' ', last_name) AS full_name,
            email,
            address_id,
            active,
            create_date
        FROM customer
        ORDER BY customer_id
        """,
    )
    df = src.merge(location_map, on="address_id", how="left")
    if df["location_key"].isna().any():
        raise RuntimeError("Some customers could not be mapped to locations.")
    df["eff_start_date"] = pd.to_datetime(df["create_date"]).dt.date
    df["eff_end_date"] = None
    df["is_current"] = True
    load_cols = [
        "customer_id", "first_name", "last_name", "full_name", "email", "location_key",
        "active", "eff_start_date", "eff_end_date", "is_current",
    ]
    load_table(dw, "dim_customer", df[load_cols])
    return read_sql(dw, "SELECT customer_id, customer_key FROM dim_customer WHERE is_current = TRUE")


def date_key(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.strftime("%Y%m%d").astype("Int64")


def load_fact_rental(oltp: Engine, dw: Engine, customer_map: pd.DataFrame, film_map: pd.DataFrame, store_map: pd.DataFrame, staff_map: pd.DataFrame) -> None:
    src = read_sql(
        oltp,
        """
        SELECT
            r.rental_id,
            r.rental_date,
            r.return_date,
            r.customer_id,
            r.staff_id,
            r.inventory_id,
            i.film_id,
            i.store_id,
            f.rental_duration AS expected_duration_days
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        ORDER BY r.rental_id
        """,
    )
    df = src.merge(customer_map, on="customer_id", how="left")
    df = df.merge(film_map, on="film_id", how="left")
    df = df.merge(store_map, on="store_id", how="left")
    df = df.merge(staff_map, on="staff_id", how="left")

    required = ["customer_key", "film_key", "store_key", "staff_key"]
    if df[required].isna().any().any():
        raise RuntimeError("Some rental rows could not be mapped to dimensions.")

    df["rental_date_actual"] = pd.to_datetime(df["rental_date"])
    df["return_date_actual"] = pd.to_datetime(df["return_date"])
    df["rental_date_key"] = date_key(df["rental_date_actual"])
    df["return_date_key"] = date_key(df["return_date_actual"])
    df["rental_duration_days"] = (df["return_date_actual"] - df["rental_date_actual"]).dt.days.astype("Int64")
    df["is_late_return"] = df["rental_duration_days"] > df["expected_duration_days"]
    df.loc[df["return_date_actual"].isna(), "is_late_return"] = None
    df["days_overdue"] = (df["rental_duration_days"] - df["expected_duration_days"]).clip(lower=0).astype("Int64")
    df.loc[df["return_date_actual"].isna(), "days_overdue"] = None
    df["rental_count"] = 1

    load_cols = [
        "rental_id", "rental_date_key", "return_date_key", "customer_key", "film_key", "store_key", "staff_key",
        "inventory_id", "rental_duration_days", "expected_duration_days", "is_late_return", "days_overdue",
        "rental_count", "rental_date_actual", "return_date_actual",
    ]
    load_table(dw, "fact_rental", df[load_cols])


def load_fact_payment(oltp: Engine, dw: Engine, customer_map: pd.DataFrame, film_map: pd.DataFrame, store_map: pd.DataFrame, staff_map: pd.DataFrame) -> None:
    src = read_sql(
        oltp,
        """
        SELECT
            p.payment_id,
            p.payment_date,
            p.customer_id,
            p.staff_id,
            p.rental_id,
            p.amount AS payment_amount,
            i.film_id,
            i.store_id
        FROM payment p
        LEFT JOIN rental r ON p.rental_id = r.rental_id
        LEFT JOIN inventory i ON r.inventory_id = i.inventory_id
        ORDER BY p.payment_id
        """,
    )
    df = src.merge(customer_map, on="customer_id", how="left")
    df = df.merge(staff_map, on="staff_id", how="left")
    df = df.merge(film_map, on="film_id", how="left")
    df = df.merge(store_map, on="store_id", how="left")

    required = ["customer_key", "staff_key", "film_key", "store_key"]
    missing = df[df[required].isna().any(axis=1)]
    if not missing.empty:
        print(f"[WARN] Dropping {len(missing)} payment rows with missing dimension keys.")
        df = df.dropna(subset=required)

    df["payment_date_actual"] = pd.to_datetime(df["payment_date"])
    df["payment_date_key"] = date_key(df["payment_date_actual"])
    df["payment_amount"] = pd.to_numeric(df["payment_amount"], errors="coerce").fillna(0)
    df["payment_count"] = 1

    load_cols = [
        "payment_id", "payment_date_key", "customer_key", "staff_key", "store_key", "rental_id", "film_key",
        "payment_amount", "payment_count", "payment_date_actual",
    ]
    load_table(dw, "fact_payment", df[load_cols])


def print_counts(dw: Engine, tables: Iterable[str]) -> None:
    print("\n[DW ROW COUNTS]")
    for table in tables:
        count = read_sql(dw, f"SELECT COUNT(*) AS count_rows FROM {table}").iloc[0, 0]
        print(f"  {table}: {int(count):,}")


def run(reset: bool = True) -> None:
    if "YOUR_PASSWORD" in OLTP_URI or "YOUR_PASSWORD" in DW_URI:
        raise RuntimeError("Set OLTP_URI and DW_URI in a .env file before running ETL.")

    oltp = engine(OLTP_URI)
    dw = engine(DW_URI)

    if reset:
        truncate_dw(dw)

    print("[ETL] Loading dimensions...")
    location_map = load_dim_location(oltp, dw)
    language_map = load_dim_language(oltp, dw)
    category_map = load_dim_category(oltp, dw)
    actor_map = load_dim_actor(oltp, dw)
    film_map = load_dim_film(oltp, dw, language_map, category_map)
    load_bridge_film_actor(oltp, dw, film_map, actor_map)
    store_map = load_dim_store(oltp, dw, location_map)
    staff_map = load_dim_staff(oltp, dw, store_map)
    customer_map = load_dim_customer(oltp, dw, location_map)

    print("[ETL] Loading facts...")
    load_fact_rental(oltp, dw, customer_map, film_map, store_map, staff_map)
    load_fact_payment(oltp, dw, customer_map, film_map, store_map, staff_map)

    print_counts(dw, [
        "dim_date", "dim_location", "dim_language", "dim_category", "dim_actor", "dim_film",
        "bridge_film_actor", "dim_store", "dim_staff", "dim_customer", "fact_rental", "fact_payment",
    ])
    print("\n[ETL] Completed successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Sakila OLTP to Movie Rental DW ETL")
    parser.add_argument("--no-reset", action="store_true", help="Do not truncate DW tables before loading.")
    args = parser.parse_args()
    run(reset=not args.no_reset)


if __name__ == "__main__":
    main()
