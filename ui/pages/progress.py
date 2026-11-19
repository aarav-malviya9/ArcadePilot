"""Progress page — charts and lab history."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st
from core import database as db
from io import BytesIO


def render():
    st.title("Progress")

    labs = db.list_labs()
    if not labs:
        st.info("No labs tracked yet. Create one in Lab Assistant.")
        return

    # Chart data
    labels = [l["name"][:20] for l in labs]
    completed = [l.get("done_tasks", 0) for l in labs]
    total_tasks = [l.get("task_count", 1) or 1 for l in labs]
    pct = [int(c / t * 100) if t > 0 else 0 for c, t in zip(completed, total_tasks)]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(labels, pct, color="#f0c040")
    ax.set_xlabel("Completion %")
    ax.set_title("Lab Progress")
    ax.set_xlim(0, 100)
    for bar, p in zip(bars, pct):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2, f"{p}%", va="center")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    st.image(buf, use_container_width=True)
    plt.close(fig)

    st.markdown("---")
    st.subheader("Lab Details")
    for lab in labs:
        with st.expander(f"{lab['name']} — {lab['status']}"):
            done = lab.get("done_tasks", 0)
            total = lab.get("task_count", 0) or 1
            pct_val = int(done / total * 100) if total > 0 else 0
            st.progress(pct_val / 100)
            st.caption(f"{done}/{total} tasks completed ({pct_val}%)")
            st.write(f"Created: {lab['created_at'][:19]}")
            st.write(f"Updated: {lab['updated_at'][:19]}")
            if lab.get("url"):
                st.markdown(f"[Open Lab]({lab['url']})")

    # Delete lab option
    st.markdown("---")
    st.subheader("Manage Labs")
    delete_lab = st.selectbox("Select lab to delete", [f"{l['name']} (#{l['id']})" for l in labs])
    if delete_lab and st.button("Delete Selected Lab"):
        lab_id = int(delete_lab.split("#")[1].rstrip(")"))
        db.delete_lab(lab_id)
        st.success(f"Deleted lab #{lab_id}")
        st.rerun()
