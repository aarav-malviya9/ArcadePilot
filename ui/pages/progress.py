"""Progress page — charts and lab history."""
from __future__ import annotations

import base64
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st
from core import database as db


def render():
    st.title("Progress")

    labs = db.list_labs()
    if not labs:
        st.info("No labs tracked yet.")
        return

    # Chart data
    labels = [l["name"][:18] for l in labs]
    pcts = [l.get("progress_pct", 0) or 0 for l in labs]
    completed_tasks = [l.get("done_tasks", 0) or 0 for l in labs]
    total_tasks = [l.get("task_count", 0) or 1 for l in labs]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Bar chart: completion %
    bars = axes[0].barh(labels[::-1], pcts[::-1], color="#f0c040")
    axes[0].set_xlabel("Completion %")
    axes[0].set_title("Lab Progress")
    axes[0].set_xlim(0, 100)
    for bar, pct in zip(bars, pcts[::-1]):
        axes[0].text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2, f"{pct}%", va="center")
    axes[0].invert_yaxis()

    # Stacked bar: tasks done vs remaining
    y_pos = range(len(labels))
    axes[1].barh(y_pos, completed_tasks[::-1], label="Completed", color="#4caf50")
    axes[1].barh(
        y_pos,
        [t - c for t, c in zip(total_tasks[::-1], completed_tasks[::-1])],
        left=completed_tasks[::-1],
        label="Remaining",
        color="#f44336",
    )
    axes[1].set_yticks(y_pos)
    axes[1].set_yticklabels([l[:15] for l in labels[::-1]])
    axes[1].set_xlabel("Tasks")
    axes[1].set_title("Tasks Completed")
    axes[1].legend()

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=150, facecolor="#0f0f0f")
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode()
    st.markdown(f'<img src="data:image/png;base64,{img_b64}" width="100%">', unsafe_allow_html=True)
    plt.close(fig)

    st.markdown("---")
    st.subheader("All Labs")

    for lab in labs:
        done = lab.get("done_tasks", 0) or 0
        total = lab.get("task_count", 0) or 1
        pct = int(done / total * 100) if total > 0 else 0
        status_emoji = {"not_started": "📋", "in_progress": "🔄", "completed": "✅", "failed": "❌", "paused": "⏸️"}
        emoji = status_emoji.get(lab["status"], "📋")

        with st.expander(f"{emoji} **{lab['name']}** — {lab['status'].title()}"):
            st.progress(pct / 100)
            if lab.get("arcadepoints", 0):
                st.caption(f"🎮 Arcade Points: {lab['arcadepoints']}")
            st.caption(f"Created: {lab['created_at'][11:19] if lab.get('created_at') else 'N/A'}")

            col_p, col_pts, col_upd = st.columns([2, 2, 1])
            with col_p:
                new_pct = st.slider("Progress %", 0, 100, pct, key=f"prog_{lab['id']}")
            with col_pts:
                pts = st.number_input("Points", min_value=0, value=lab.get("arcadepoints") or 0, key=f"pts_{lab['id']}")
            with col_upd:
                if st.button("Update", key=f"upd_{lab['id']}"):
                    new_status = "completed" if new_pct >= 100 else "in_progress" if new_pct > 0 else "not_started"
                    db.update_lab_status(lab["id"], new_status, progress_pct=new_pct, arcadepoints=pts)
                    db.log_activity("info", f"Updated {lab['name']}: {new_pct}%, {pts} points")
                    st.success("Updated!")
                    st.rerun()

            if st.button("Delete Lab", key=f"del_{lab['id']}"):
                db.delete_lab(lab["id"])
                db.log_activity("warning", f"Deleted lab '{lab['name']}' (#{lab['id']})")
                st.success(f"Deleted {lab['name']}")
                st.rerun()
