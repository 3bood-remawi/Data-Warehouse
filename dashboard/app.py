"""
Movie Rental Data Warehouse Dashboard

A simple Streamlit dashboard to demonstrate the output of the Sakila OLTP ->
Movie Rental Data Warehouse ETL process.

This dashboard is intentionally presentation-focused:
- It does not replace the report.
- It does not perform ETL.
- It reads from the already-loaded Data Warehouse and visualizes business answers.

Run:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


load_dotenv()

DEFAULT_DW_URI = "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/movie_rental_dw"
ENV_DW_URI = os.getenv("DW_URI", DEFAULT_DW_URI)


@dataclass
class QueryResult:
    name: str
    data: pd.DataFrame


BUSINESS_QUESTIONS = {
    "Monthly revenue trend": "How does rental revenue change over time?",
    "Top rented films": "Which films are rented the most?",
    "Revenue by category": "Which movie categories generate the highest revenue?",
    "Store performance": "Which store performs better in rentals and revenue?",
    "Top customers": "Who are the highest-spending customers?",
    "Late returns": "Which categories have more late returns?",
}


QUERIES: Dict[str, str] = {
    "kpis": """
        SELECT
            (SELECT COALESCE(SUM(payment_amount), 0) FROM fact_payment) AS total_revenue,
            (SELECT COUNT(*) FROM fact_rental) AS total_rentals,
            (SELECT COUNT(*) FROM dim_customer WHERE is_current = TRUE) AS total_customers,
            (SELECT COUNT(*) FROM dim_film) AS total_films,
            (SELECT COUNT(*) FROM dim_store) AS total_stores,
            (SELECT COUNT(*) FROM dim_staff) AS total_staff
    """,
    "monthly_revenue": """
        SELECT
            d.year,
            d.month_number,
            d.month_name,
            CONCAT(d.year, '-', LPAD(d.month_number, 2, '0')) AS month_label,
            ROUND(SUM(fp.payment_amount), 2) AS total_revenue,
            COUNT(*) AS payment_count
        FROM fact_payment fp
        JOIN dim_date d ON fp.payment_date_key = d.date_key
        GROUP BY d.year, d.month_number, d.month_name
        ORDER BY d.year, d.month_number
    """,
    "top_films_by_rentals": """
        SELECT
            f.title,
            f.category_name,
            COUNT(*) AS total_rentals
        FROM fact_rental fr
        JOIN dim_film f ON fr.film_key = f.film_key
        GROUP BY f.title, f.category_name
        ORDER BY total_rentals DESC, f.title ASC
        LIMIT 10
    """,
    "revenue_by_category": """
        SELECT
            f.category_name,
            ROUND(SUM(fp.payment_amount), 2) AS total_revenue,
            COUNT(*) AS payment_count
        FROM fact_payment fp
        JOIN dim_film f ON fp.film_key = f.film_key
        GROUP BY f.category_name
        ORDER BY total_revenue DESC
    """,
    "store_performance": """
        WITH rental_summary AS (
            SELECT store_key, COUNT(*) AS total_rentals
            FROM fact_rental
            GROUP BY store_key
        ),
        payment_summary AS (
            SELECT store_key, ROUND(SUM(payment_amount), 2) AS total_revenue, COUNT(*) AS total_payments
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
        ORDER BY total_revenue DESC
    """,
    "top_customers": """
        SELECT
            c.customer_id,
            c.full_name,
            l.city,
            l.country,
            ROUND(SUM(fp.payment_amount), 2) AS total_spent,
            COUNT(*) AS payment_count
        FROM fact_payment fp
        JOIN dim_customer c ON fp.customer_key = c.customer_key
        JOIN dim_location l ON c.location_key = l.location_key
        GROUP BY c.customer_id, c.full_name, l.city, l.country
        ORDER BY total_spent DESC, payment_count DESC
        LIMIT 10
    """,
    "late_returns_by_category": """
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
        ORDER BY late_return_percentage DESC, late_returns DESC
    """,
    "rental_duration_by_category": """
        SELECT
            f.category_name,
            ROUND(AVG(fr.rental_duration_days), 2) AS avg_rental_duration_days,
            ROUND(AVG(fr.days_overdue), 2) AS avg_days_overdue,
            COUNT(*) AS total_rentals
        FROM fact_rental fr
        JOIN dim_film f ON fr.film_key = f.film_key
        WHERE fr.rental_duration_days IS NOT NULL
        GROUP BY f.category_name
        ORDER BY avg_rental_duration_days DESC
    """,
    "dw_counts": """
        SELECT 'dim_date' AS table_name, COUNT(*) AS row_count FROM dim_date
        UNION ALL SELECT 'dim_location', COUNT(*) FROM dim_location
        UNION ALL SELECT 'dim_customer', COUNT(*) FROM dim_customer
        UNION ALL SELECT 'dim_language', COUNT(*) FROM dim_language
        UNION ALL SELECT 'dim_category', COUNT(*) FROM dim_category
        UNION ALL SELECT 'dim_actor', COUNT(*) FROM dim_actor
        UNION ALL SELECT 'dim_film', COUNT(*) FROM dim_film
        UNION ALL SELECT 'bridge_film_actor', COUNT(*) FROM bridge_film_actor
        UNION ALL SELECT 'dim_store', COUNT(*) FROM dim_store
        UNION ALL SELECT 'dim_staff', COUNT(*) FROM dim_staff
        UNION ALL SELECT 'fact_rental', COUNT(*) FROM fact_rental
        UNION ALL SELECT 'fact_payment', COUNT(*) FROM fact_payment
    """,
}


def make_demo_data() -> Dict[str, pd.DataFrame]:
    """Fallback sample data so the dashboard can still be shown if MySQL is not connected."""
    return {
        "kpis": pd.DataFrame(
            [
                {
                    "total_revenue": 67416.51,
                    "total_rentals": 16044,
                    "total_customers": 599,
                    "total_films": 1000,
                    "total_stores": 2,
                    "total_staff": 2,
                }
            ]
        ),
        "monthly_revenue": pd.DataFrame(
            {
                "month_label": ["2005-05", "2005-06", "2005-07", "2005-08"],
                "total_revenue": [4824.43, 9631.88, 28368.91, 24072.13],
                "payment_count": [1156, 2311, 6709, 5686],
            }
        ),
        "top_films_by_rentals": pd.DataFrame(
            {
                "title": ["BUCKET BROTHERHOOD", "ROCKETEER MOTHER", "SCALAWAG DUCK", "FORWARD TEMPLE"],
                "category_name": ["Travel", "Foreign", "Music", "Games"],
                "total_rentals": [34, 33, 32, 32],
            }
        ),
        "revenue_by_category": pd.DataFrame(
            {
                "category_name": ["Sports", "Sci-Fi", "Animation", "Drama", "Comedy"],
                "total_revenue": [5314.21, 4756.98, 4656.30, 4587.39, 4383.58],
                "payment_count": [1179, 1101, 1065, 1060, 941],
            }
        ),
        "store_performance": pd.DataFrame(
            {
                "store_id": [1, 2],
                "city": ["Lethbridge", "Woodridge"],
                "country": ["Canada", "Australia"],
                "total_rentals": [8040, 8004],
                "total_revenue": [33679.79, 33736.72],
                "total_payments": [8021, 8023],
            }
        ),
        "top_customers": pd.DataFrame(
            {
                "customer_id": [526, 148, 144, 137, 178],
                "full_name": ["ELEANOR HUNT", "CLARA SHAW", "EVELYN MORGAN", "RHONDA KENNEDY", "MARION SNYDER"],
                "city": ["Saint-Denis", "Aparecida de Goiania", "Mandaluyong", "Molodetno", "Tanza"],
                "country": ["Reunion", "Brazil", "Philippines", "Belarus", "Philippines"],
                "total_spent": [211.55, 195.58, 194.61, 194.61, 194.61],
                "payment_count": [45, 46, 42, 38, 39],
            }
        ),
        "late_returns_by_category": pd.DataFrame(
            {
                "category_name": ["Travel", "Sports", "Sci-Fi", "Comedy", "Drama"],
                "total_rentals": [837, 1179, 1101, 941, 1060],
                "late_returns": [313, 411, 378, 307, 332],
                "late_return_percentage": [37.40, 34.86, 34.33, 32.62, 31.32],
            }
        ),
        "rental_duration_by_category": pd.DataFrame(
            {
                "category_name": ["Travel", "Animation", "Sports", "Documentary"],
                "avg_rental_duration_days": [5.25, 5.12, 5.01, 4.92],
                "avg_days_overdue": [1.40, 1.31, 1.22, 1.19],
                "total_rentals": [837, 1065, 1179, 953],
            }
        ),
        "dw_counts": pd.DataFrame(
            {
                "table_name": [
                    "dim_date",
                    "dim_location",
                    "dim_customer",
                    "dim_language",
                    "dim_category",
                    "dim_actor",
                    "dim_film",
                    "bridge_film_actor",
                    "dim_store",
                    "dim_staff",
                    "fact_rental",
                    "fact_payment",
                ],
                "row_count": [2191, 603, 599, 1, 16, 200, 1000, 5462, 2, 2, 16044, 16044],
            }
        ),
    }


@st.cache_resource(show_spinner=False)
def get_engine(db_uri: str) -> Engine:
    return create_engine(db_uri, pool_pre_ping=True)


@st.cache_data(show_spinner=False, ttl=60)
def run_query(db_uri: str, query: str) -> pd.DataFrame:
    engine = get_engine(db_uri)
    return pd.read_sql(text(query), con=engine)


def load_all_data(db_uri: str, demo_mode: bool) -> tuple[Dict[str, pd.DataFrame], str | None]:
    if demo_mode:
        return make_demo_data(), None

    data: Dict[str, pd.DataFrame] = {}
    try:
        for name, query in QUERIES.items():
            data[name] = run_query(db_uri, query)
        return data, None
    except SQLAlchemyError as exc:
        return make_demo_data(), str(exc)
    except Exception as exc:  # keeps presentation safe if a driver/env issue happens
        return make_demo_data(), str(exc)


def money(value: float) -> str:
    return f"${value:,.2f}"


def number(value: float) -> str:
    return f"{int(value):,}"


def show_header(demo_mode: bool, error: str | None) -> None:
    st.title("Movie Rental Data Warehouse Dashboard")
    st.caption("A simple visualization layer for the Sakila OLTP → ETL → Data Warehouse project")

    if demo_mode:
        st.info("Demo mode is ON. The dashboard is showing sample values. Turn it off from the sidebar after your MySQL DW is ready.")
    elif error:
        st.warning(
            "Could not connect to the Data Warehouse, so the dashboard is showing demo data. "
            "Check DW_URI, MySQL, and whether ETL has been loaded."
        )
        with st.expander("Show technical connection error"):
            st.code(error)
    else:
        st.success("Connected to movie_rental_dw successfully.")


def show_overview(data: Dict[str, pd.DataFrame]) -> None:
    kpis = data["kpis"].iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", money(float(kpis["total_revenue"])))
    col2.metric("Total Rentals", number(kpis["total_rentals"]))
    col3.metric("Total Customers", number(kpis["total_customers"]))

    col4, col5, col6 = st.columns(3)
    col4.metric("Total Films", number(kpis["total_films"]))
    col5.metric("Stores", number(kpis["total_stores"]))
    col6.metric("Staff", number(kpis["total_staff"]))

    st.subheader("Project Flow")
    st.markdown(
        """
        **Operational OLTP database** records rentals and payments.  
        **ETL** extracts operational data, transforms it into analytical shape, and loads it into fact and dimension tables.  
        **Data Warehouse** answers business questions using aggregated queries.
        """
    )

    flow = pd.DataFrame(
        {
            "Layer": ["OLTP Source", "ETL", "Data Warehouse", "Dashboard"],
            "Role": [
                "Sakila normalized operational database",
                "Extract, clean, join, calculate keys and measures",
                "Fact and dimension tables for analysis",
                "Charts and KPIs for business questions",
            ],
        }
    )
    st.dataframe(flow, use_container_width=True, hide_index=True)

    st.subheader("Monthly Revenue Trend")
    monthly = data["monthly_revenue"].copy()
    if not monthly.empty:
        chart_data = monthly.set_index("month_label")[["total_revenue"]]
        st.line_chart(chart_data)
        st.dataframe(monthly, use_container_width=True, hide_index=True)


def show_business_questions(data: Dict[str, pd.DataFrame]) -> None:
    st.subheader("Business Questions Answered by the DW")
    st.dataframe(
        pd.DataFrame(
            [{"Dashboard Section": key, "Business Question": value} for key, value in BUSINESS_QUESTIONS.items()]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Top Rented Films")
        df = data["top_films_by_rentals"].copy()
        if not df.empty:
            st.bar_chart(df.set_index("title")[["total_rentals"]])
            st.dataframe(df, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("### Revenue by Category")
        df = data["revenue_by_category"].copy()
        if not df.empty:
            st.bar_chart(df.set_index("category_name")[["total_revenue"]])
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("### Store Performance")
        df = data["store_performance"].copy()
        if not df.empty:
            chart_df = df.copy()
            chart_df["store_label"] = "Store " + chart_df["store_id"].astype(str)
            st.bar_chart(chart_df.set_index("store_label")[["total_revenue", "total_rentals"]])
            st.dataframe(df, use_container_width=True, hide_index=True)

    with c4:
        st.markdown("### Top Customers by Spending")
        df = data["top_customers"].copy()
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    c5, c6 = st.columns(2)
    with c5:
        st.markdown("### Late Returns by Category")
        df = data["late_returns_by_category"].copy()
        if not df.empty:
            st.bar_chart(df.set_index("category_name")[["late_return_percentage"]])
            st.dataframe(df, use_container_width=True, hide_index=True)

    with c6:
        st.markdown("### Rental Duration by Category")
        df = data["rental_duration_by_category"].copy()
        if not df.empty:
            st.bar_chart(df.set_index("category_name")[["avg_rental_duration_days", "avg_days_overdue"]])
            st.dataframe(df, use_container_width=True, hide_index=True)


def show_etl_pipeline() -> None:
    st.subheader("ETL Pipeline Explanation")
    st.markdown(
        """
        This page is for the doctor/demo discussion. It explains what happens before the dashboard is shown.
        """
    )

    steps = pd.DataFrame(
        [
            {
                "ETL Step": "Extract",
                "What happens": "Read normalized OLTP tables such as rental, payment, film, customer, inventory, staff, store, address, city, and country.",
                "Example": "payment → rental → inventory → film",
            },
            {
                "ETL Step": "Transform",
                "What happens": "Clean values, convert dates, create date keys, join normalized tables, calculate rental duration, late return flag, and overdue days.",
                "Example": "payment_date → payment_date_key",
            },
            {
                "ETL Step": "Load Dimensions",
                "What happens": "Load descriptive context first so fact tables can reference dimension surrogate keys.",
                "Example": "dim_customer, dim_film, dim_store, dim_staff, dim_date",
            },
            {
                "ETL Step": "Load Facts",
                "What happens": "Load measurable business events after dimensions are ready.",
                "Example": "fact_rental and fact_payment",
            },
            {
                "ETL Step": "Analyze",
                "What happens": "Run analytical queries on the DW instead of the OLTP schema.",
                "Example": "Monthly revenue, top films, store performance",
            },
        ]
    )
    st.dataframe(steps, use_container_width=True, hide_index=True)

    st.markdown("### Loading Order")
    st.code(
        """dim_date
→ dim_location
→ dim_language / dim_category / dim_actor
→ dim_film
→ bridge_film_actor
→ dim_store
→ dim_staff
→ dim_customer
→ fact_rental
→ fact_payment""",
        language="text",
    )


def show_model() -> None:
    st.subheader("High-Level Dimensional Model")
    st.markdown(
        """
        The dashboard is based on a hybrid star/snowflake dimensional model.  
        The **facts** store business events and numeric measures.  
        The **dimensions** provide descriptive context for filtering and grouping.
        """
    )

    model = pd.DataFrame(
        [
            {"Table": "fact_rental", "Type": "Fact", "Grain": "One row per rental transaction", "Main Measures": "rental_count, rental_duration_days, days_overdue"},
            {"Table": "fact_payment", "Type": "Fact", "Grain": "One row per payment transaction", "Main Measures": "payment_amount, payment_count"},
            {"Table": "dim_date", "Type": "Dimension", "Grain": "One row per calendar date", "Main Measures": "N/A"},
            {"Table": "dim_customer", "Type": "Dimension", "Grain": "One row per current customer version", "Main Measures": "N/A"},
            {"Table": "dim_film", "Type": "Dimension", "Grain": "One row per film", "Main Measures": "N/A"},
            {"Table": "dim_store", "Type": "Dimension", "Grain": "One row per store", "Main Measures": "N/A"},
            {"Table": "dim_staff", "Type": "Dimension", "Grain": "One row per staff member", "Main Measures": "N/A"},
            {"Table": "dim_location", "Type": "Dimension", "Grain": "One row per address/location", "Main Measures": "N/A"},
        ]
    )
    st.dataframe(model, use_container_width=True, hide_index=True)

    st.markdown("### Relationship Summary")
    st.code(
        """fact_payment  → dim_date, dim_customer, dim_staff, dim_store, dim_film
fact_rental   → dim_date, dim_customer, dim_staff, dim_store, dim_film
dim_film      → dim_category, dim_language
bridge_film_actor → dim_film, dim_actor""",
        language="text",
    )


def show_data_quality(data: Dict[str, pd.DataFrame]) -> None:
    st.subheader("DW Validation / Row Counts")
    st.markdown(
        """
        This page helps during the demo because it proves that the ETL actually loaded data into the DW tables.
        """
    )

    counts = data["dw_counts"].copy()
    st.dataframe(counts, use_container_width=True, hide_index=True)
    if not counts.empty:
        st.bar_chart(counts.set_index("table_name")[["row_count"]])

    st.markdown("### What to say in the presentation")
    st.info(
        "We validate the ETL by checking that dimensions and fact tables have rows after loading. "
        "Then we use analytical queries on the DW, not on the original OLTP database."
    )


def show_run_guide(db_uri: str) -> None:
    st.subheader("How to Run the Demo")
    st.markdown("Use this section as your checklist before presenting.")

    st.code(
        """# 1) Install dashboard requirements
pip install -r dashboard/requirements.txt

# 2) Make sure MySQL is running
# 3) Import Sakila OLTP database
# 4) Run sql/create_dw_schema.sql
# 5) Run ETL script to load movie_rental_dw
# 6) Start the dashboard
streamlit run dashboard/app.py""",
        language="bash",
    )

    st.markdown("### Current connection setting")
    safe_uri = db_uri.replace(os.getenv("DB_PASSWORD", ""), "***") if os.getenv("DB_PASSWORD") else db_uri
    st.code(safe_uri, language="text")

    st.markdown("### Recommended explanation to the doctor")
    st.success(
        "This dashboard is not the main project. It is a visualization layer that proves our ETL and Data Warehouse can answer business questions."
    )


def main() -> None:
    st.set_page_config(page_title="Movie Rental DW Dashboard", page_icon="🎬", layout="wide")

    with st.sidebar:
        st.header("Dashboard Settings")
        db_uri = st.text_input("DW_URI", value=ENV_DW_URI, type="password")
        demo_mode = st.checkbox("Use demo data", value=("YOUR_PASSWORD" in db_uri))
        st.caption("Turn demo mode off after `movie_rental_dw` is loaded.")

        st.divider()
        page = st.radio(
            "Pages",
            [
                "Overview",
                "Business Questions",
                "ETL Pipeline",
                "Dimensional Model",
                "Validation",
                "Run Guide",
            ],
        )

    data, error = load_all_data(db_uri, demo_mode=demo_mode)
    show_header(demo_mode=demo_mode, error=error)

    if page == "Overview":
        show_overview(data)
    elif page == "Business Questions":
        show_business_questions(data)
    elif page == "ETL Pipeline":
        show_etl_pipeline()
    elif page == "Dimensional Model":
        show_model()
    elif page == "Validation":
        show_data_quality(data)
    elif page == "Run Guide":
        show_run_guide(db_uri)


if __name__ == "__main__":
    main()
