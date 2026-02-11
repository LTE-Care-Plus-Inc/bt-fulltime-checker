import streamlit as st
import pandas as pd
from io import BytesIO

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="Full Time BT Monitor", layout="wide")
st.title("Full Time BT Monitor")
st.caption("PASS = >130 hours in all 3 selected months (Completed=Yes + Direct Service BT only)")

# =====================================================
# UPLOAD
# =====================================================
uploaded_file = st.file_uploader(
    "Upload Aloha Appointment Billing File",
    type=["csv", "xlsx"]
)

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
COL_UNITS = "Units"
COL_COMPLETED = "Completed"
COL_SERVICE = "Service Name"

required_cols = [COL_STAFF, COL_DATE, COL_UNITS, COL_COMPLETED, COL_SERVICE]
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
# FILTER: Service Name = Direct Service BT
# =====================================================
df[COL_SERVICE] = df[COL_SERVICE].astype(str).str.strip()
df = df[df[COL_SERVICE] == "Direct Service BT"].copy()

# =====================================================
# NORMALIZE
# =====================================================
df[COL_DATE] = pd.to_datetime(df[COL_DATE], errors="coerce")
df = df.dropna(subset=[COL_DATE]).copy()

df[COL_UNITS] = pd.to_numeric(df[COL_UNITS], errors="coerce").fillna(0)

# Convert Units → Hours (15 min units)
df["Hours"] = df[COL_UNITS] / 4

df["YearMonth"] = df[COL_DATE].dt.to_period("M").astype(str)

# =====================================================
# MONTHLY TOTALS
# =====================================================
monthly_hours = (
    df.groupby([COL_STAFF, "YearMonth"], as_index=False)["Hours"]
      .sum()
)

# =====================================================
# MONTH SELECTOR
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

selected_months = sorted(selected_months)

# =====================================================
# PIVOT TABLE (Month headers with actual hours)
# =====================================================
pivot = (
    monthly_hours[monthly_hours["YearMonth"].isin(selected_months)]
    .pivot_table(
        index=COL_STAFF,
        columns="YearMonth",
        values="Hours",
        aggfunc="sum",
        fill_value=0
    )
    .reset_index()
)

# Ensure selected months exist
for m in selected_months:
    if m not in pivot.columns:
        pivot[m] = 0

pivot = pivot[[COL_STAFF] + selected_months]

# =====================================================
# PASS / NO PASS
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
    st.info("No BTs met full-time requirement.")
else:
    st.dataframe(pass_df, use_container_width=True)

# =====================================================
# EXCEL DOWNLOAD (Two Sheets)
# =====================================================
def create_excel(pass_df, no_pass_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pass_df.to_excel(writer, sheet_name="PASS", index=False)
        no_pass_df.to_excel(writer, sheet_name="NO PASS", index=False)
    return output.getvalue()

excel_data = create_excel(pass_df, no_pass_df)

st.download_button(
    label="⬇️ Download Full-Time BT",
    data=excel_data,
    file_name="Full_Time_BT_List.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
