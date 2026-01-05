import streamlit as st
import pandas as pd
import os
import altair as alt
import json
from datetime import datetime

st.set_page_config(page_title="Metro Dashboard", layout="wide", initial_sidebar_state="collapsed")

# ===============================
# CUSTOM CSS
# ===============================
st.markdown("""
<style>
    /* Main background */
    .main {
        background: linear-gradient(135deg, #0a0f0d 0%, #0f1713 100%);
    }
    
    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #0f1713 0%, #1a2520 100%);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
        border: 1px solid rgba(52, 211, 153, 0.15);
        margin-bottom: 20px;
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(135deg, #064e3b 0%, #065f46 100%);
        padding: 12px 20px;
        border-radius: 10px;
        margin-bottom: 15px;
        border-left: 4px solid #10b981;
    }
    
    .section-title {
        color: #10b981 !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        margin: 0 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Headers */
    h1, h2, h3, h4 {
        color: #f1f5f9 !important;
        font-weight: 700 !important;
        text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.5);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #10b981 !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 16px !important;
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        background: #1a2520 !important;
        border-radius: 10px !important;
        border: 2px solid #065f46 !important;
        color: #f1f5f9 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(15, 23, 19, 0.5);
        border-radius: 15px;
        padding: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(26, 37, 32, 0.5);
        border-radius: 10px;
        color: #94a3b8;
        font-weight: 600;
        padding: 12px 24px;
        border: none;
    }
    
    .stTabs [aria-selected="true"] {
        background: #1a2520;
        color: #10b981;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
    }
    
    /* Info boxes */
    .stAlert {
        background: #1a2520;
        border-radius: 10px;
        border-left: 4px solid #10b981;
        color: #cbd5e1;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0f0d 0%, #0f1713 100%);
        border-right: 1px solid #065f46;
    }
    
    [data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }
    
    /* Chart containers */
    .chart-container {
        background: linear-gradient(135deg, #0f1713 0%, #1a2520 100%);
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
        margin-top: 20px;
        border: 1px solid rgba(52, 211, 153, 0.15);
    }
    
    /* Checkbox */
    .stCheckbox {
        color: #f1f5f9 !important;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# CONFIG
# ===============================
DATA_DIR = "data/2025"
CONFIG_FILE = "config/stations.json"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("config", exist_ok=True)

MONTHS = [f"2025-{str(i).zfill(2)}" for i in range(1, 13)]

# Required columns in uploaded data
REQUIRED_COLUMNS = {
    "Start": "Station where ride started",
    "End": "Station where ride ended",
    "User Id": "Unique identifier for user",
    "Signup Local Date": "Date user signed up",
    "Start Date Local": "Date and time ride started",
    "Duration": "Ride duration in minutes",
    "Rating": "User rating (1-5 stars)"
}

START_COL = "Start"
END_COL = "End"
USER_COL = "User Id"
SIGNUP_COL = "Signup Local Date"
START_DATE_COL = "Start Date Local"
DURATION_COL = "Duration"
RATING_COL = "Rating"

# User segmentation thresholds
LIGHT_USER_MIN = 2
LIGHT_USER_MAX = 5
HEAVY_USER_MIN = 6

# Rating thresholds
MIN_RATING = 1
MAX_RATING = 5
POSITIVE_RATING_MIN = 4

# ===============================
# STATION CONFIG MANAGEMENT
# ===============================
DEFAULT_STATIONS = {
    "Koleyet El Banat": "كليه البنات",
    "Safaa Hegazy": "صفاء",
    "Al-Ahram": "الاهرام",
    "Heliopolis": "هليوبوليس",
    "Alf Maskan": "الف مسكن",
    "Haroun": "هارون",
}

def load_stations():
    """Load station configuration from file or use defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading station config: {e}")
            return DEFAULT_STATIONS
    return DEFAULT_STATIONS

def save_stations(stations):
    """Save station configuration to file."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(stations, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving station config: {e}")
        return False

STATIONS = load_stations()

# ===============================
# HELPERS
# ===============================
def validate_dataframe(df):
    """Validate that dataframe contains all required columns."""
    missing = [col for col in REQUIRED_COLUMNS.keys() if col not in df.columns]
    
    if missing:
        error_msg = f"Missing required columns: {', '.join(missing)}\n\n"
        error_msg += "Required columns:\n"
        for col, desc in REQUIRED_COLUMNS.items():
            status = "✓" if col in df.columns else "✗"
            error_msg += f"{status} {col}: {desc}\n"
        return False, missing, error_msg
    
    return True, [], ""

def clean_df(df):
    """Clean and standardize dataframe columns and data types."""
    df.columns = (
        df.columns.astype(str)
        .str.replace("\xa0", " ", regex=False)
        .str.strip()
    )
    
    for col in [START_DATE_COL, SIGNUP_COL]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    
    if DURATION_COL in df.columns:
        df[DURATION_COL] = pd.to_numeric(df[DURATION_COL], errors="coerce")
    
    if RATING_COL in df.columns:
        df[RATING_COL] = pd.to_numeric(df[RATING_COL], errors="coerce")
    
    return df

def filter_by_station(df, col, keyword):
    """Filter dataframe by station keyword."""
    return df[df[col].astype(str).str.contains(keyword, na=False, case=False)]

def prev_month(month):
    """Get previous month string."""
    y, m = month.split("-")
    m = int(m)
    return f"{y}-{m-1:02d}" if m > 1 else None

def trend_delta(current, previous):
    """Calculate percentage change between current and previous values."""
    if previous in (None, 0) or current is None:
        return None
    return (current - previous) / previous * 100

# ===============================
# LOAD MONTH (CACHED)
# ===============================
@st.cache_data(show_spinner=False)
def load_month(month):
    """Load data for a specific month from CSV or Excel file."""
    if not month:
        return None
    
    for ext in ["csv", "xlsx"]:
        path = os.path.join(DATA_DIR, f"{month}.{ext}")
        if os.path.exists(path):
            try:
                if ext == "csv":
                    df = pd.read_csv(path)
                else:
                    df = pd.read_excel(path)
                return clean_df(df)
            except Exception as e:
                st.error(f"Error loading {path}: {e}")
                return None
    
    return None

def get_uploaded_months():
    """Get list of months that have data uploaded."""
    uploaded = []
    for m in MONTHS:
        for ext in ["csv", "xlsx"]:
            if os.path.exists(os.path.join(DATA_DIR, f"{m}.{ext}")):
                uploaded.append(m)
                break
    return uploaded

# ===============================
# STATION METRICS (CACHED)
# ===============================
@st.cache_data(show_spinner=False, ttl=3600)
def compute_station_data(df, month):
    """Compute all metrics for all stations for a given month."""
    out = {}
    
    for station, keyword in STATIONS.items():
        starts = filter_by_station(df, START_COL, keyword)
        ends = filter_by_station(df, END_COL, keyword)
        
        started_ended = df[
            df[START_COL].astype(str).str.contains(keyword, na=False, case=False) &
            df[END_COL].astype(str).str.contains(keyword, na=False, case=False)
        ]
        
        riders = starts.copy()
        total_riders = riders[USER_COL].nunique()
        
        new_signups = riders[
            riders[SIGNUP_COL].dt.to_period("M") == pd.Period(month)
        ][USER_COL].nunique()
        
        rides_per_user = riders.groupby(USER_COL).size()
        
        rating_series = pd.to_numeric(riders[RATING_COL], errors="coerce")
        rating_series = rating_series[rating_series.between(MIN_RATING, MAX_RATING)]
        avg_rating = rating_series.mean() if len(rating_series) > 0 else None
        
        positive_pct = (
            (rating_series >= POSITIVE_RATING_MIN).sum() / len(rating_series) * 100
            if len(rating_series) > 0 else None
        )
        
        out[station] = {
            "starts_df": starts,
            "ends_df": ends,
            "total_starts": len(starts),
            "total_ends": len(ends),
            "started_ended": len(started_ended),
            "total_riders": total_riders,
            "new_signups": new_signups,
            "new_signup_pct": (new_signups / total_riders * 100) if total_riders else 0,
            "one_time": (rides_per_user == 1).sum(),
            "light": ((rides_per_user >= LIGHT_USER_MIN) & (rides_per_user <= LIGHT_USER_MAX)).sum(),
            "heavy": (rides_per_user >= HEAVY_USER_MIN).sum(),
            "avg_duration": riders[DURATION_COL].mean(),
            "avg_rating": avg_rating,
            "positive_rating_pct": positive_pct,
            "total_ratings": len(rating_series),
        }
    
    return out

# ===============================
# CHART DATA (CACHED)
# ===============================
@st.cache_data(show_spinner=False, ttl=3600)
def compute_heatmap(starts_df):
    """Compute heatmap data for rides by day and hour."""
    df = starts_df.copy()
    df["Hour"] = df[START_DATE_COL].dt.hour
    df["Day"] = df[START_DATE_COL].dt.day_name()
    return df.groupby(["Day", "Hour"]).size().reset_index(name="Rides")

@st.cache_data(show_spinner=False, ttl=3600)
def compute_hourly_trend(starts_df):
    """Compute hourly ride counts."""
    df = starts_df.copy()
    df["Hour"] = df[START_DATE_COL].dt.hour
    return df.groupby("Hour").size().reset_index(name="Rides").sort_values("Hour")

@st.cache_data(show_spinner=False, ttl=3600)
def compute_monthly_trend(station_keyword):
    """Compute monthly trend for a specific station across all uploaded months."""
    rows = []
    uploaded_months = get_uploaded_months()
    
    for m in uploaded_months:
        df = load_month(m)
        if df is None:
            continue
        
        starts = filter_by_station(df, START_COL, station_keyword)
        rows.append({"Month": m, "Start Rides": len(starts)})
    
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False, ttl=3600)
def compute_station_comparison(df, month):
    """Compute comparison metrics across all stations."""
    station_data = compute_station_data(df, month)
    
    rows = []
    for station, data in station_data.items():
        rows.append({
            "Station": station,
            "Total Starts": data["total_starts"],
            "Total Riders": data["total_riders"],
            "Avg Duration": data["avg_duration"],
            "Avg Rating": data["avg_rating"],
            "Heavy Users": data["heavy"],
        })
    
    return pd.DataFrame(rows)

# ===============================
# EXPORT FUNCTIONS
# ===============================
def export_to_csv(df, filename):
    """Convert DataFrame to CSV for download."""
    return df.to_csv(index=False).encode('utf-8')

# ===============================
# SIDEBAR
# ===============================
with st.sidebar:
    st.markdown("# 📂 Data Management")
    
    # Station Configuration
    with st.expander("⚙️ Manage Stations"):
        st.markdown("**Current Stations:**")
        for station, keyword in STATIONS.items():
            st.text(f"• {station}")
        
        st.markdown("---")
        st.markdown("**Add New Station:**")
        new_station = st.text_input("Station Name")
        new_keyword = st.text_input("Station Keyword")
        
        if st.button("➕ Add Station", use_container_width=True):
            if new_station and new_keyword:
                STATIONS[new_station] = new_keyword
                if save_stations(STATIONS):
                    st.success(f"✅ Added {new_station}")
                    st.rerun()
            else:
                st.warning("⚠️ Provide both name and keyword")
    
    # Monthly Data Uploads
    st.markdown("---")
    st.markdown("### 📅 Upload Monthly Data")
    
    upload_month = st.selectbox("Select Month", MONTHS, key="upload_month_select")
    
    file = st.file_uploader(
        f"Upload data for {upload_month}",
        type=["csv", "xlsx"],
        key="file_uploader",
    )
    
    if file:
        try:
            ext = file.name.split(".")[-1]
            
            if ext == "csv":
                df_up = pd.read_csv(file)
            else:
                df_up = pd.read_excel(file)
            
            is_valid, missing, error_msg = validate_dataframe(df_up)
            
            if not is_valid:
                st.error("❌ Invalid format")
                with st.expander("Show Details"):
                    st.text(error_msg)
            else:
                df_up = clean_df(df_up)
                path = os.path.join(DATA_DIR, f"{upload_month}.{ext}")
                
                if ext == "csv":
                    df_up.to_csv(path, index=False)
                else:
                    df_up.to_excel(path, index=False)
                
                st.success(f"✅ Saved {len(df_up):,} records")
                st.cache_data.clear()
                
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    # Show uploaded months
    st.markdown("---")
    st.markdown("### 📊 Uploaded Data")
    uploaded = get_uploaded_months()
    
    if uploaded:
        for m in uploaded:
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"✓ {m}")
            if col2.button("🗑️", key=f"del_{m}"):
                for e in ["csv", "xlsx"]:
                    path = os.path.join(DATA_DIR, f"{m}.{e}")
                    if os.path.exists(path):
                        os.remove(path)
                st.cache_data.clear()
                st.rerun()
    else:
        st.info("No data uploaded yet")

# ===============================
# MAIN HEADER
# ===============================
st.markdown("<h1 style='text-align: center; font-size: 48px; margin-bottom: 10px;'>🚇 Metro Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 18px; margin-bottom: 30px;'>Real-time Station Performance Insights</p>", unsafe_allow_html=True)

# ===============================
# MAIN CONTROLS
# ===============================
col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

with col1:
    station = st.selectbox("🚉 Station", list(STATIONS.keys()), label_visibility="collapsed", placeholder="Select Station")

with col2:
    month = st.selectbox("📅 Month", MONTHS, label_visibility="collapsed", placeholder="Select Month")

with col3:
    show_comparison = st.checkbox("📊 Compare", value=True, help="Compare with previous month")

with col4:
    view_mode = st.selectbox("View", ["Station", "All Stations"], label_visibility="collapsed")

# ===============================
# LOAD DATA
# ===============================
df = load_month(month)

if df is None:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.warning(f"⚠️ No data available for {month}. Please upload data using the sidebar.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

is_valid, missing, error_msg = validate_dataframe(df)
if not is_valid:
    st.error("❌ Data validation failed")
    st.text(error_msg)
    st.stop()

# ===============================
# STATION VIEW
# ===============================
if view_mode == "Station":
    station_data = compute_station_data(df, month)[station]
    
    pm = prev_month(month) if show_comparison else None
    prev_df = load_month(pm) if pm else None
    prev_data = compute_station_data(prev_df, pm)[station] if prev_df is not None else None
    
    starts_df = station_data["starts_df"]
    
    # Hero Stats
    st.markdown(f"<h2 style='text-align: center; margin-top: 30px;'>{station} • {month}</h2>", unsafe_allow_html=True)
    
    def metric(col, label, value, prev_value, fmt=None, help_text=None):
        """Display metric with optional comparison."""
        delta = trend_delta(value, prev_value) if show_comparison and prev_value else None
        formatted_value = fmt.format(value) if fmt and value is not None else value
        
        col.metric(
            label,
            formatted_value if formatted_value is not None else "N/A",
            f"{delta:.1f}%" if delta is not None else None,
            delta_color="normal",
            help=help_text
        )
    
    # RIDE PERFORMANCE
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'><p class='section-title'>🚴 Ride Performance</p></div>", unsafe_allow_html=True)
    
    cols = st.columns(5)
    metric(cols[0], "🚀 Total Starts", station_data["total_starts"], 
           prev_data["total_starts"] if prev_data else None,
           help_text="Rides starting at this station")
    metric(cols[1], "🏁 Total Ends", station_data["total_ends"], 
           prev_data["total_ends"] if prev_data else None,
           help_text="Rides ending at this station")
    metric(cols[2], "🔄 Round Trips", station_data["started_ended"], 
           prev_data["started_ended"] if prev_data else None,
           help_text="Rides that started and ended here")
    metric(cols[3], "⏱️ Avg Duration", station_data["avg_duration"], 
           prev_data["avg_duration"] if prev_data else None, "{:.1f} min",
           help_text="Average ride length")
    metric(cols[4], "⭐ Rating", station_data["avg_rating"], 
           prev_data["avg_rating"] if prev_data else None, "{:.2f}",
           help_text="Average rating (1-5)")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # USER PERFORMANCE
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'><p class='section-title'>👥 User Performance</p></div>", unsafe_allow_html=True)
    
    cols2 = st.columns(5)
    metric(cols2[0], "👥 Total Riders", station_data["total_riders"], 
           prev_data["total_riders"] if prev_data else None,
           help_text="Unique users")
    metric(cols2[1], "🆕 New Signups", station_data["new_signups"], 
           prev_data["new_signups"] if prev_data else None,
           help_text="New users this month")
    metric(cols2[2], "1️⃣ One-Time", station_data["one_time"], 
           prev_data["one_time"] if prev_data else None,
           help_text="Users with 1 ride")
    metric(cols2[3], "💡 Light Users", station_data["light"], 
           prev_data["light"] if prev_data else None,
           help_text=f"Users with {LIGHT_USER_MIN}-{LIGHT_USER_MAX} rides")
    metric(cols2[4], "🔥 Heavy Users", station_data["heavy"], 
           prev_data["heavy"] if prev_data else None,
           help_text=f"Users with {HEAVY_USER_MIN}+ rides")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Charts
    if not starts_df.empty:
        # Heatmap and Hourly side by side
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
            st.markdown("#### 🔥 Ride Heatmap")
            heat = compute_heatmap(starts_df)
            st.altair_chart(
                alt.Chart(heat).mark_rect().encode(
                    x=alt.X("Hour:O", title="Hour"),
                    y=alt.Y("Day:O", sort=[
                        "Monday", "Tuesday", "Wednesday", "Thursday", 
                        "Friday", "Saturday", "Sunday"
                    ], title="Day"),
                    color=alt.Color("Rides:Q", scale=alt.Scale(scheme="greens"), title="Rides"),
                    tooltip=["Day", "Hour", "Rides"]
                ).properties(height=300),
                use_container_width=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
            st.markdown("#### ⏰ Hourly Distribution")
            hourly = compute_hourly_trend(starts_df)
            st.altair_chart(
                alt.Chart(hourly).mark_area(
                    line={'color':'#10b981'},
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='#0f1713', offset=0),
                               alt.GradientStop(color='#10b981', offset=1)],
                        x1=1, x2=1, y1=1, y2=0
                    )
                ).encode(
                    x=alt.X("Hour:O", title="Hour"),
                    y=alt.Y("Rides:Q", title="Rides"),
                    tooltip=["Hour", "Rides"]
                ).properties(height=300),
                use_container_width=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Monthly Trend
        trend_df = compute_monthly_trend(STATIONS[station])
        
        if not trend_df.empty and len(trend_df) > 1:
            st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
            st.markdown("#### 📈 Monthly Trend")
            st.altair_chart(
                alt.Chart(trend_df).mark_line(
                    point=alt.OverlayMarkDef(color="#10b981", size=100),
                    color="#10b981",
                    strokeWidth=3
                ).encode(
                    x=alt.X("Month:O", title="Month"),
                    y=alt.Y("Start Rides:Q", title="Rides"),
                    tooltip=["Month", "Start Rides"]
                ).properties(height=300),
                use_container_width=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

# ===============================
# ALL STATIONS VIEW
# ===============================
else:
    comparison = compute_station_comparison(df, month)
    
    st.markdown(f"<h2 style='text-align: center; margin-top: 30px;'>All Stations • {month}</h2>", unsafe_allow_html=True)
    
    # Metric selector
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        metric_col = st.selectbox(
            "Select Metric",
            ["Total Starts", "Total Riders", "Heavy Users", "Avg Duration", "Avg Rating"]
        )
    with col2:
        csv_comp = export_to_csv(comparison, f"comparison_{month}.csv")
        st.download_button(
            label="📥 Export CSV",
            data=csv_comp,
            file_name=f"comparison_{month}.csv",
            mime="text/csv",
            use_container_width=True
        )
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Chart
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    chart_data = comparison.sort_values(metric_col, ascending=False)
    
    st.altair_chart(
        alt.Chart(chart_data).mark_bar(
            cornerRadiusTopRight=10,
            cornerRadiusBottomRight=10
        ).encode(
            x=alt.X(f"{metric_col}:Q", title=metric_col),
            y=alt.Y("Station:N", sort="-x", title=""),
            color=alt.Color(
                "Station:N",
                scale=alt.Scale(scheme="greens"),
                legend=None
            ),
            tooltip=["Station", metric_col]
        ).properties(height=400),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Data table
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.markdown("### 📋 Detailed Comparison")
    st.dataframe(
        comparison.style.format({
            "Avg Duration": "{:.1f}",
            "Avg Rating": "{:.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )
    st.markdown("</div>", unsafe_allow_html=True)