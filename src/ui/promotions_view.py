"""
Promotions Explorer component: visual table, search, filters, and JSON inspection.
"""

from typing import Dict, Any, List
import streamlit as st
import pandas as pd
from src.sfcc.client import SFCCPromotionsClient
from src.config import get_session_settings


def render_promotions_explorer():
    """Render the interactive SFCC promotions explorer."""
    st.subheader("📋 Active Promotions in Salesforce Commerce Cloud")

    cfg = get_session_settings()
    if not cfg.is_sfcc_configured():
        st.warning("Please configure your SFCC credentials in the sidebar to inspect promotions.")
        return

    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        refresh = st.button("🔄 Refresh Data", use_container_width=True)

    # Cache promotions in session state so we don't query every rerun unless requested
    if "cached_promotions" not in st.session_state or refresh:
        with st.spinner("Fetching promotions from SFCC..."):
            try:
                client = SFCCPromotionsClient()
                result = client.list_promotions(limit=50)
                st.session_state["cached_promotions"] = result
            except Exception as e:
                st.error(f"Failed to fetch promotions: {str(e)}")
                return

    data = st.session_state.get("cached_promotions", {})
    promotions: List[Dict[str, Any]] = data.get("hits", data.get("data", []))

    if not promotions:
        st.info(f"No promotions found on site '{cfg.sfcc_site_id}'.")
        return

    # Metrics Row
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    total_count = data.get("total", len(promotions))
    active_count = sum(1 for p in promotions if p.get("enabled", False))
    disabled_count = len(promotions) - active_count
    product_count = sum(1 for p in promotions if p.get("promotionClass") == "product")

    m_col1.metric("Total Promos", total_count)
    m_col2.metric("Enabled", active_count)
    m_col3.metric("Disabled", disabled_count)
    m_col4.metric("Product Promos", product_count)

    st.markdown("---")

    # Search & Filter
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_query = st.text_input("🔍 Search by ID or Name", "")
    with f_col2:
        class_filter = st.selectbox("Class Filter", ["All", "product", "order", "shipping"])
    with f_col3:
        status_filter = st.selectbox("Status Filter", ["All", "Enabled Only", "Disabled Only"])

    # Filter data
    filtered = []
    for p in promotions:
        p_id = str(p.get("id", ""))
        name_dict = p.get("name", {})
        if isinstance(name_dict, dict):
            p_name = name_dict.get("default") or next(iter(name_dict.values()), "")
        else:
            p_name = str(name_dict)
        p_class = str(p.get("promotionClass", ""))
        enabled = bool(p.get("enabled", False))

        if search_query:
            q = search_query.lower()
            if q not in p_id.lower() and q not in p_name.lower():
                continue

        if class_filter != "All" and p_class != class_filter:
            continue

        if status_filter == "Enabled Only" and not enabled:
            continue
        if status_filter == "Disabled Only" and enabled:
            continue

        filtered.append({
            "id": p_id,
            "name": p_name,
            "promotionClass": p_class,
            "enabled": enabled,
            "archived": p.get("archived", False),
            "raw": p,
        })

    st.caption(f"Showing {len(filtered)} of {total_count} promotions")

    # Display Table
    if filtered:
        table_data = [
            {
                "ID": item["id"],
                "Name": item["name"],
                "Class": item["promotionClass"],
                "Status": "🟢 Enabled" if item["enabled"] else "🔴 Disabled",
                "Archived": "Yes" if item["archived"] else "No",
            }
            for item in filtered
        ]
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)

        # Inspect details accordion
        with st.expander("🔍 Inspect Full Promotion Payloads"):
            selected_id = st.selectbox("Select a Promotion to inspect JSON", [item["id"] for item in filtered])
            selected_item = next((item for item in filtered if item["id"] == selected_id), None)
            if selected_item:
                st.json(selected_item["raw"])
    else:
        st.info("No promotions match the current filter criteria.")
