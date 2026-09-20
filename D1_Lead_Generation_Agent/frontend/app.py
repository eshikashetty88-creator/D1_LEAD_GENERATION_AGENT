import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

# Streamlit Cloud can store secrets in st.secrets.
try:
    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    if "SERPER_API_KEY" in st.secrets:
        os.environ["SERPER_API_KEY"] = st.secrets["SERPER_API_KEY"]
    if "GEMINI_MODEL" in st.secrets:
        os.environ["GEMINI_MODEL"] = st.secrets["GEMINI_MODEL"]
except Exception:
    pass

from agents.models import ICP
from agents.graph import run_pipeline
from agents.exporter import to_dataframe, write_csv, write_hubspot_csv


st.set_page_config(
    page_title="D1 Lead Generation Agent",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Autonomous Lead Generation & Qualification Agent")
st.caption("D1 • Discovery → Compliance → Enrichment → Deduplication → Scoring → Export")

with st.sidebar:
    st.header("Ideal Customer Profile")
    industry = st.text_input("Industry", "B2B SaaS")
    min_employees = st.number_input("Minimum employees", min_value=1, value=50)
    max_employees = st.number_input("Maximum employees", min_value=1, value=500)
    geography = st.text_input("Geography", "India")
    signals = st.text_input("Signals of interest", "Hiring / Growth")
    target_roles = st.text_input(
        "Target job titles",
        "Founder, CEO, CTO, Head of Security",
    )
    lead_count = st.slider("Number of leads", 3, 25, 10)

    demo_mode = st.toggle(
        "Mock/demo fallback",
        value=not bool(os.getenv("SERPER_API_KEY")),
        help="Use safe sample records when live source access is unavailable.",
    )

    generate = st.button("🚀 Generate Leads", type="primary", use_container_width=True)

if "result" not in st.session_state:
    st.session_state.result = None

if generate:
    icp = ICP(
        industry=industry,
        min_employees=int(min_employees),
        max_employees=int(max_employees),
        geography=geography,
        signals=signals,
        target_roles=target_roles,
        lead_count=int(lead_count),
    )

    if demo_mode:
        os.environ["FORCE_MOCK"] = "1"
    else:
        os.environ.pop("FORCE_MOCK", None)

    # The graph itself also falls back to mock data when discovery has no usable results.
    with st.spinner("Running discovery, robots checks, enrichment, deduplication and scoring..."):
        try:
            st.session_state.result = run_pipeline(icp)
        except Exception as exc:
            st.error(f"Pipeline failed: {exc}")

result = st.session_state.result

if result:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Discovered", result.discovered_count)
    c2.metric("Duplicates Removed", result.duplicates_removed)
    c3.metric("Unique Leads", result.unique_count)
    c4.metric("Qualified (≥60)", result.qualified_count)
    c5.metric("Average Score", result.average_score)

    st.divider()
    st.subheader("📋 Lead Results")

    df = to_dataframe(result.leads).sort_values("icp_score", ascending=False)

    score_filter = st.slider("Minimum ICP score", 0, 100, 0)
    filtered = df[df["icp_score"] >= score_filter]

    st.dataframe(
        filtered[
            [
                "company_name", "website", "industry", "location",
                "employee_count", "contact_name", "job_title",
                "icp_score", "data_confidence", "source_url",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("🧠 Transparent Scoring")
    for _, row in filtered.iterrows():
        with st.expander(f"{row['company_name']} — {row['icp_score']}/100"):
            st.write(f"**Qualification:** {row.get('qualification', 'Needs review')}")
            st.write(row["score_reasoning"])
            st.write(
                f"Industry {row.get('industry_points',0)}/30 • "
                f"Size {row.get('size_points',0)}/20 • "
                f"Geography {row.get('geography_points',0)}/15 • "
                f"Signals {row.get('signal_points',0)}/15 • "
                f"Technology {row.get('technology_points',0)}/10 • "
                f"Confidence {row.get('confidence_points',0)}/10"
            )
            st.write(f"**Sources:** {row['source_url']}")
            if row.get("source_urls",[]):
                for source in row.get("source_urls",[]):
                    st.write(source)

    st.subheader("📥 Exports")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    hubspot_path = write_hubspot_csv(result.leads)
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name="d1_leads.csv",
        mime="text/csv",
        use_container_width=True,
    )

    hubspot_df = pd.read_csv(hubspot_path)
    st.download_button(
        "Download HubSpot-style CSV",
        data=hubspot_df.to_csv(index=False).encode("utf-8"),
        file_name="d1_hubspot_import.csv",
        mime="text/csv",
        use_container_width=True,
    )

    with st.expander("🔐 robots.txt / compliance log"):
        if result.skipped_urls:
            st.write("Skipped URLs:")
            for url in result.skipped_urls:
                st.write(f"- {url}")
        else:
            st.write("No disallowed URLs were fetched in this run.")
        for log in result.logs:
            if "ROBOTS" in log.upper():
                st.code(log)

    with st.expander("⚙️ Pipeline logs"):
        for log in result.logs:
            st.write(log)

    st.info(
        "Refresh is re-runnable: click Generate Leads again. "
        "Search/page cache reduces repeated requests; robots.txt is checked before page fetching."
    )
else:
    st.markdown(
        """
        ### How it works

        **1. ICP intake** → **2. Discovery Agent** → **3. robots.txt compliance**
        → **4. Enrichment Agent** → **5. Deduplication** → **6. Scoring Agent**
        → **7. CSV / HubSpot export**

        **Demo ICP:** B2B SaaS • India • 50–500 employees • Hiring/Growth
        """
    )
