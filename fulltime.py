import streamlit as st
import pandas as pd

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Full Time BT Monitor", layout="wide")
st.title("Full Time BT Monitor")
st.caption("Shows monthly hours by BT. PASS = >130 hours in all 3 selected months (Completed=Yes only).")

# =====================================================
# UPLOAD
# =====================================================
uploaded_file = st.file_uploader("Upload Aloha Appointment Billing File", type=["csv", "xlsx"])
if not uploaded_file:
    st.stop()

# =====================================================
# LOAD
# =====================================================
if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
else:
    df = pd.read_excel(uploaded_file)

# =====================================================
# REQUIRED COLUMNS
# =====================================================
COL_STAFF = "Staff Name"
COL_DATE = "Appt. Date"
COL_HOURS = "Billing Hours"
COL_COMPLETED = "Completed"

required_cols = [COL_STAFF, COL_DATE, COL_HOURS, COL_COMPLETED]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

# =====================================================
# FILTER: Completed = Yes
# =====================================================
df[COL_COMPLETED] = df[COL_COMPLETED].astype(str).str.strip().str.lower()
df = df[df[COL_COMPLETED] == "yes"].copy()

# =====================================================
# NORMALIZE
# =====================================================
df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce")
df = df.dropna(subset=[COL_DATE]).copy()

df[COL_HOURS] = pd.to_numeric(df[COL_HOURS], errors="coerce").fillna(0)

# Build YearMonth like 2025-10
df["YearMonth"] = df[COL_DATE].dt.to_period("M").astype(str)

# =====================================================
# MONTHLY TOTALS
# =====================================================
monthly_hours = (
    df.groupby([COL_STAFF, "YearMonth"], as_index=False)[COL_HOURS]
      .sum()
      .rename(columns={COL_HOURS: "Monthly Hours"})
)

# =====================================================
# MONTH SELECTOR (3 months)
# =====================================================
all_months = sorted(monthly_hours["YearMonth"].unique())

default_months = all_months[-3:] if len(all_months) >= 3 else all_months
selected_months = st.multiselect(
    "Select exactly 3 months to evaluate full-time status",
    options=all_months,
    default=default_months
)

if len(selected_months) != 3:
    st.warning("Please select exactly 3 months.")
    st.stop()

selected_months = sorted(selected_months)  # ensure order like 2025-10, 2025-11, 2025-12

# =====================================================
# PIVOT: headers are the months, values are hours
# =====================================================
pivot = (
    monthly_hours[monthly_hours["YearMonth"].isin(selected_months)]
    .pivot_table(
        index=COL_STAFF,
        columns="YearMonth",
        values="Monthly Hours",
        aggfunc="sum",
        fill_value=0
    )
    .reset_index()
)

# Ensure the selected months exist as columns (even if missing for some staff)
for m in selected_months:
    if m not in pivot.columns:
        pivot[m] = 0

# Reorder columns: Staff Name + the 3 month headers
pivot = pivot[[COL_STAFF] + selected_months]

# =====================================================
# PASS / NO PASS
# PASS = >130 in ALL 3 selected months
# =====================================================
pass_mask = (pivot[selected_months] > 130).all(axis=1)

pass_df = pivot[pass_mask].copy()
pass_df["Status"] = "PASS"

no_pass_df = pivot[~pass_mask].copy()
no_pass_df["Status"] = "NO PASS"

# =====================================================
# DISPLAY
# =====================================================
st.subheader("✅ PASS (Full-Time BTs)")
if pass_df.empty:
    st.info("No BTs met the full-time requirement for the selected 3 months.")
else:
    st.dataframe(pass_df, use_container_width=True)

# =====================================================
# DOWNLOAD (PASS ONLY)
# =====================================================
csv = pass_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download Full-Time BT",
    data=csv,
    file_name="Full_Time_BT_List.csv",
    mime="text/csv"
)
