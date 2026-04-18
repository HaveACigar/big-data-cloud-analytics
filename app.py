import joblib
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Big Data & Cloud Analytics", page_icon="☁️", layout="wide", initial_sidebar_state="collapsed")
TEMPLATE = "plotly_dark"


@st.cache_resource
def load_artifacts():
    return joblib.load("models.pkl")


def main():
    arts = load_artifacts()
    st.title("☁️ Big Data & Cloud Analytics")
    st.markdown("Partitioned event data pipeline with warehouse-style KPI marts, performance summaries, and cloud-scale analytics patterns.")

    tabs = st.tabs(["Overview", "Daily KPIs", "Country & Platform", "Funnel", "Data Quality"])

    with tabs[0]:
        tests = arts["tests"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows Loaded", f"{tests['rows_loaded']:,}")
        c2.metric("Partitions", f"{tests['partitions_detected']:,}")
        c3.metric("Null Country Rows", tests['null_country_rows'])
        c4.metric("Negative Revenue Rows", tests['negative_revenue_rows'])

    with tabs[1]:
        daily = arts["daily_kpis"]
        fig = px.line(daily, x="event_day", y=["total_events", "active_users", "revenue"], title="Daily KPI Trends", template=TEMPLATE)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(daily, use_container_width=True, hide_index=True)

    with tabs[2]:
        perf = arts["country_perf"]
        fig = px.treemap(perf, path=["country", "platform", "product_category"], values="revenue", color="avg_purchase_value", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(perf, use_container_width=True, hide_index=True)

    with tabs[3]:
        funnel = arts["funnel"]
        fig = px.funnel(funnel, x="events", y="event_type", title="Event Funnel", template=TEMPLATE)
        st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        st.dataframe(pd.DataFrame(list(arts["tests"].items()), columns=["test", "value"]), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
