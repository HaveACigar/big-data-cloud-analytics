import os
import joblib
import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

RNG = np.random.default_rng(42)


def generate_events(n=250000):
    start = pd.Timestamp("2024-01-01")
    timestamps = start + pd.to_timedelta(RNG.integers(0, 90 * 24 * 60, size=n), unit="m")
    df = pd.DataFrame({
        "event_ts": timestamps,
        "user_id": RNG.integers(1, 50001, size=n),
        "session_id": RNG.integers(1, 120001, size=n),
        "country": RNG.choice(["US", "Canada", "UK", "Germany", "India"], size=n, p=[0.45, 0.12, 0.12, 0.11, 0.2]),
        "platform": RNG.choice(["web", "ios", "android"], size=n, p=[0.46, 0.22, 0.32]),
        "event_type": RNG.choice(["view", "search", "add_to_cart", "purchase"], size=n, p=[0.56, 0.18, 0.17, 0.09]),
        "product_category": RNG.choice(["subscription", "accessories", "audio", "navigation", "charging"], size=n),
    })
    df["revenue"] = np.where(df["event_type"] == "purchase", np.round(RNG.gamma(2.0, 45.0, size=n), 2), 0.0)
    df["event_date"] = df["event_ts"].dt.date.astype(str)
    return df


def write_partitioned_parquet(df):
    os.makedirs("data/events", exist_ok=True)
    table = pa.Table.from_pandas(df)
    pq.write_to_dataset(table, root_path="data/events", partition_cols=["event_date", "country"])


def main():
    df = generate_events()
    write_partitioned_parquet(df)

    con = duckdb.connect()
    con.execute("""
        create or replace view events as
        select * from read_parquet('data/events/**/*.parquet', hive_partitioning=true)
    """)

    daily_kpis = con.execute("""
        select
            cast(event_ts as date) as event_day,
            count(*) as total_events,
            count(distinct user_id) as active_users,
            count(distinct session_id) as sessions,
            sum(revenue) as revenue,
            sum(case when event_type = 'purchase' then 1 else 0 end) as purchases
        from events
        group by 1
        order by 1
    """).df()

    country_perf = con.execute("""
        select
            country,
            platform,
            product_category,
            count(*) as events,
            count(distinct user_id) as users,
            sum(revenue) as revenue,
            avg(case when event_type = 'purchase' then revenue end) as avg_purchase_value
        from events
        group by 1,2,3
        order by revenue desc
        limit 200
    """).df()

    funnel = con.execute("""
        select
            event_type,
            count(*) as events
        from events
        group by 1
        order by events desc
    """).df()

    tests = {
        "rows_loaded": int(con.execute("select count(*) from events").fetchone()[0]),
        "partitions_detected": int(con.execute("select count(distinct event_date || '-' || country) from events").fetchone()[0]),
        "null_country_rows": int(con.execute("select count(*) from events where country is null").fetchone()[0]),
        "negative_revenue_rows": int(con.execute("select count(*) from events where revenue < 0").fetchone()[0]),
    }

    joblib.dump(
        {
            "daily_kpis": daily_kpis,
            "country_perf": country_perf,
            "funnel": funnel,
            "tests": tests,
        },
        "models.pkl",
        compress=3,
    )


if __name__ == "__main__":
    main()
