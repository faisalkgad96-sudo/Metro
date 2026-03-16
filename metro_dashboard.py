import streamlit as st
import pandas as pd
import os
import altair as alt
import json
import io
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
BASE_DATA_DIR = "data"
CONFIG_FILE = "config/stations.json"
AVAILABLE_YEARS = [2025, 2026]

os.makedirs(BASE_DATA_DIR, exist_ok=True)
os.makedirs("config", exist_ok=True)

# Create directories for each year
for year in AVAILABLE_YEARS:
    os.makedirs(os.path.join(BASE_DATA_DIR, str(year)), exist_ok=True)

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
def get_months_for_year(year):
    """Generate list of months for a given year."""
    return [f"{year}-{str(i).zfill(2)}" for i in range(1, 13)]

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
    y, m = int(y), int(m)
    if m > 1:
        return f"{y}-{m-1:02d}"
    elif y > min(AVAILABLE_YEARS):
        return f"{y-1}-12"
    return None

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
    
    year = month.split("-")[0]
    data_dir = os.path.join(BASE_DATA_DIR, year)
    
    for ext in ["csv", "xlsx"]:
        path = os.path.join(data_dir, f"{month}.{ext}")
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

def get_uploaded_months(year=None):
    """Get list of months that have data uploaded."""
    uploaded = []
    years_to_check = [year] if year else AVAILABLE_YEARS
    
    for y in years_to_check:
        data_dir = os.path.join(BASE_DATA_DIR, str(y))
        months = get_months_for_year(y)
        for m in months:
            for ext in ["csv", "xlsx"]:
                if os.path.exists(os.path.join(data_dir, f"{m}.{ext}")):
                    uploaded.append(m)
                    break
    
    return sorted(uploaded)

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


def _excel_serial_date(dt):
    """Convert datetime to Excel serial date (days since 1899-12-30)."""
    if pd.isna(dt):
        return None
    if hasattr(dt, "to_pydatetime"):
        dt = dt.to_pydatetime()
    return (dt.replace(tzinfo=None) - datetime(1899, 12, 30)).days


def _daily_stats_for_station(df, month, station_name):
    """For one station and month, return daily arrays and user-segment counts."""
    keyword = STATIONS.get(station_name)
    if not keyword:
        return None
    station_data = compute_station_data(df, month).get(station_name)
    if not station_data:
        return None
    starts_df = station_data["starts_df"]
    ends_df = station_data["ends_df"]
    if starts_df.empty or START_DATE_COL not in starts_df.columns:
        return None

    year, month_num = int(month.split("-")[0]), int(month.split("-")[1])
    last_day = pd.Timestamp(year=year, month=month_num, day=1) + pd.offsets.MonthEnd(0)
    num_days = last_day.day

    start_rides_by_day = [0] * num_days
    end_rides_by_day = [0] * num_days
    new_signups_by_day = [0] * num_days
    total_starts_by_day = [0] * num_days
    total_ends_by_day = [0] * num_days
    duration_sum_by_day = [0.0] * num_days
    duration_count_by_day = [0] * num_days
    rating_sum_by_day = [0.0] * num_days
    rating_count_by_day = [0] * num_days

    # Count unique users who signed up on each day (for new signup by day)
    signup_date_to_users = {}
    for _, row in starts_df.iterrows():
        dt = row.get(START_DATE_COL)
        if pd.isna(dt):
            continue
        d = dt.day if hasattr(dt, "day") else pd.Timestamp(dt).day
        if 1 <= d <= num_days:
            idx = d - 1
            start_rides_by_day[idx] += 1
            total_starts_by_day[idx] += 1
            dur = row.get(DURATION_COL)
            if pd.notna(dur):
                duration_sum_by_day[idx] += float(dur)
                duration_count_by_day[idx] += 1
            rt = row.get(RATING_COL)
            if pd.notna(rt) and MIN_RATING <= rt <= MAX_RATING:
                rating_sum_by_day[idx] += float(rt)
                rating_count_by_day[idx] += 1
            try:
                su = row.get(SIGNUP_COL)
                if pd.notna(su):
                    su_ts = pd.Timestamp(su)
                    if su_ts.year == year and su_ts.month == month_num:
                        sd = su_ts.day
                        if sd not in signup_date_to_users:
                            signup_date_to_users[sd] = set()
                        signup_date_to_users[sd].add(row.get(USER_COL))
            except Exception:
                pass
    for sd, users in signup_date_to_users.items():
        if 1 <= sd <= num_days:
            new_signups_by_day[sd - 1] = len(users)

    for _, row in ends_df.iterrows():
        dt = row.get(START_DATE_COL)
        if pd.isna(dt):
            continue
        d = dt.day if hasattr(dt, "day") else pd.Timestamp(dt).day
        if 1 <= d <= num_days:
            end_rides_by_day[d - 1] += 1
            total_ends_by_day[d - 1] += 1

    avg_duration_by_day = []
    for i in range(num_days):
        if duration_count_by_day[i] > 0:
            avg_duration_by_day.append(round(duration_sum_by_day[i] / duration_count_by_day[i], 2))
        else:
            avg_duration_by_day.append(None)
    avg_rating_by_day = []
    for i in range(num_days):
        if rating_count_by_day[i] > 0:
            avg_rating_by_day.append(round(rating_sum_by_day[i] / rating_count_by_day[i], 2))
        else:
            avg_rating_by_day.append(None)

    rides_per_user = starts_df.groupby(USER_COL).size()
    ride_distribution = rides_per_user.value_counts().sort_index()
    one_time = int((rides_per_user == 1).sum())
    light = int(((rides_per_user >= LIGHT_USER_MIN) & (rides_per_user <= LIGHT_USER_MAX)).sum())
    heavy = int((rides_per_user >= HEAVY_USER_MIN).sum())
    total_riders = one_time + light + heavy

    return {
        "num_days": num_days,
        "start_rides_by_day": start_rides_by_day,
        "end_rides_by_day": end_rides_by_day,
        "total_starts_by_day": total_starts_by_day,
        "total_ends_by_day": total_ends_by_day,
        "new_signups_by_day": new_signups_by_day,
        "avg_duration_by_day": avg_duration_by_day,
        "avg_rating_by_day": avg_rating_by_day,
        "ride_distribution": ride_distribution,
        "one_time": one_time,
        "light": light,
        "heavy": heavy,
        "total_riders": total_riders,
        "station_data": station_data,
    }


def _hourly_heatmap_for_station(starts_df):
    """Rows = day names (Sun-Sat), Cols = hour 0-23, values = ride count."""
    if starts_df.empty or START_DATE_COL not in starts_df.columns:
        return pd.DataFrame()
    df = starts_df.copy()
    df["Hour"] = df[START_DATE_COL].dt.hour
    df["Day"] = df[START_DATE_COL].dt.day_name()
    grp = df.groupby(["Day", "Hour"]).size()
    pivot = grp.unstack(fill_value=0)
    day_order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for d in day_order:
        if d not in pivot.index:
            pivot.loc[d] = 0
    pivot = pivot.reindex(day_order)
    pivot = pivot.reindex(columns=range(24), fill_value=0)
    pivot["Total"] = pivot.sum(axis=1)
    return pivot


def _compute_overall_trend():
    """Compute monthly trend of key metrics across all stations."""
    rows = []
    uploaded_months = get_uploaded_months()

    for m in uploaded_months:
        df_m = load_month(m)
        if df_m is None:
            continue

        is_valid, _, _ = validate_dataframe(df_m)
        if not is_valid:
            continue

        rating_series = pd.to_numeric(df_m.get(RATING_COL), errors="coerce")
        rating_series = rating_series[rating_series.between(MIN_RATING, MAX_RATING)]

        rows.append(
            {
                "Month": m,
                "Total Rides": len(df_m),
                "Unique Users": df_m[USER_COL].nunique(),
                "Average Duration (min)": df_m[DURATION_COL].mean()
                if DURATION_COL in df_m.columns
                else None,
                "Average Rating": rating_series.mean()
                if len(rating_series) > 0
                else None,
            }
        )

    return pd.DataFrame(rows)


def _compute_station_trend(station_name):
    """Compute monthly trend of metrics for a single station across all months."""
    keyword = STATIONS.get(station_name)
    if not keyword:
        return pd.DataFrame()

    rows = []
    uploaded_months = get_uploaded_months()

    for m in uploaded_months:
        df_m = load_month(m)
        if df_m is None:
            continue

        is_valid, _, _ = validate_dataframe(df_m)
        if not is_valid:
            continue

        station_data_all = compute_station_data(df_m, m)
        data = station_data_all.get(station_name)
        if not data:
            continue

        rows.append(
            {
                "Month": m,
                "Total Starts": data["total_starts"],
                "Total Riders": data["total_riders"],
                "Heavy Users": data["heavy"],
                "Avg Duration": data["avg_duration"],
                "Avg Rating": data["avg_rating"],
            }
        )

    return pd.DataFrame(rows)


def export_month_to_excel(df, month):
    """Build Excel report for the selected month only: same KPIs/metrics/layout for copy-paste into a bigger workbook."""
    output = io.BytesIO()
    year, month_num = int(month.split("-")[0]), int(month.split("-")[1])
    first_day = datetime(year, month_num, 1)
    last_day_dt = pd.Timestamp(year=year, month=month_num, day=1) + pd.offsets.MonthEnd(0)
    num_days = last_day_dt.day
    serial_start = _excel_serial_date(first_day)
    serial_end = _excel_serial_date(last_day_dt)

    # Template sheet order (match "Metro GL3 (November - 2025).xlsx"); then any other stations
    station_order = [
        "Safaa Hegazy",
        "Heliopolis",
        "Al-Ahram",
        "Koleyet El Banat",
        "Alf Maskan",
        "Haroun",
    ]
    ordered = [s for s in station_order if s in STATIONS]
    rest = [s for s in STATIONS.keys() if s not in station_order]
    stations_to_export = ordered + rest

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#065f46", "font_color": "#FFFFFF", "border": 1, "align": "center"}
        )
        label_fmt = workbook.add_format({"bold": True, "border": 1, "align": "left"})
        cell_fmt = workbook.add_format({"border": 1, "align": "center"})
        pct_fmt = workbook.add_format({"border": 1, "align": "center", "num_format": "0.0%"})
        date_fmt = workbook.add_format(
            {"border": 1, "align": "center", "num_format": "dd/mm/yyyy"}
        )

        for station_name in stations_to_export:
            daily = _daily_stats_for_station(df, month, station_name)
            if not daily:
                continue
            sd = daily["station_data"]
            sheet_name = station_name[:31]
            ws = workbook.add_worksheet(sheet_name)
            ws.freeze_panes(1, 1)

            # Monthly aggregates (one column = selected month)
            total_start_rides = sd["total_starts"]
            total_end_rides = sd["total_ends"]
            avg_dur = sd.get("avg_duration")
            total_duration = (avg_dur * total_start_rides) if (avg_dur is not None and total_start_rides) else None
            new_signups_total = sum(daily["new_signups_by_day"])
            total_riders = daily["total_riders"]
            started_ended = sd["started_ended"]
            started_ended_pct = (started_ended / total_start_rides * 100) if total_start_rides else 0
            new_signup_pct_over_riders = (new_signups_total / total_riders * 100) if total_riders else 0

            # Row 1: station name, month start date, month end date
            ws.write(0, 0, station_name, label_fmt)
            ws.write(0, 1, serial_start, date_fmt)
            ws.write(0, 2, serial_end, date_fmt)

            # Section 1: Ride metrics — one column (month total)
            ws.write(2, 0, "Day / Period", label_fmt)
            ws.write(2, 1, serial_start, date_fmt)
            ws.write(3, 0, "Start Rides", label_fmt)
            ws.write(3, 1, total_start_rides, cell_fmt)
            ws.write(4, 0, "End Rides", label_fmt)
            ws.write(4, 1, total_end_rides, cell_fmt)
            ws.write(5, 0, "Total", label_fmt)
            ws.write(5, 1, round(total_duration, 2) if total_duration is not None else "", cell_fmt)
            ws.write(6, 0, "AVG Ride Duration", label_fmt)
            ws.write(6, 1, sd["avg_duration"] if sd.get("avg_duration") is not None else "", cell_fmt)
            ws.write(7, 0, "Rating (After Trip)", label_fmt)
            ws.write(7, 1, sd["avg_rating"] if sd.get("avg_rating") is not None else "", cell_fmt)

            # Right after first table: rides that start & end at station + % of start rides
            ws.write(8, 0, f"#of Rides Start & Ended {station_name}", label_fmt)
            ws.write(8, 1, started_ended, cell_fmt)
            ws.write(9, 0, "% of Start Rides", label_fmt)
            ws.write(9, 1, started_ended_pct / 100.0, pct_fmt)

            # Third table: total riders, new signups, new signups over total riders
            ws.write(11, 0, "Day / Period", label_fmt)
            ws.write(11, 1, serial_start, date_fmt)
            ws.write(12, 0, "Number Of Users", label_fmt)
            ws.write(12, 1, total_riders, cell_fmt)
            ws.write(13, 0, "New-Signup", label_fmt)
            ws.write(13, 1, new_signups_total, cell_fmt)
            ws.write(14, 0, "New Signup % (over total riders)", label_fmt)
            ws.write(14, 1, new_signup_pct_over_riders / 100.0, pct_fmt)

            # Block 4: 1-Time User distribution (unchanged — already monthly)
            dist = daily["ride_distribution"]
            ride_counts = sorted(dist.index.tolist())
            ws.write(21, 0, "1-Time User", label_fmt)
            for col_idx, rc in enumerate(ride_counts[: min(31, len(ride_counts))]):
                ws.write(21, col_idx + 1, int(rc), cell_fmt)
            ws.write(22, 0, "Number Of Users", label_fmt)
            for col_idx, rc in enumerate(ride_counts[: min(31, len(ride_counts))]):
                ws.write(22, col_idx + 1, int(dist[rc]), cell_fmt)
            ws.write(23, 0, "--", label_fmt)
            total_dist = dist.sum()
            for col_idx, rc in enumerate(ride_counts[: min(31, len(ride_counts))]):
                pct = (dist[rc] / total_dist) if total_dist else 0
                ws.write(23, col_idx + 1, pct, pct_fmt)

            # Summary: 1-Time, Light-user, Heavy-user — Rows 27–30
            ws.write(26, 0, "1-Time", label_fmt)
            ws.write(26, 1, daily["one_time"], cell_fmt)
            ws.write(26, 2, (daily["one_time"] / total_riders) if total_riders else 0, pct_fmt)
            ws.write(27, 0, "Light-user", label_fmt)
            ws.write(27, 1, daily["light"], cell_fmt)
            ws.write(27, 2, (daily["light"] / total_riders) if total_riders else 0, pct_fmt)
            ws.write(28, 0, "Heavy-user", label_fmt)
            ws.write(28, 1, daily["heavy"], cell_fmt)
            ws.write(28, 2, (daily["heavy"] / total_riders) if total_riders else 0, pct_fmt)
            ws.write(29, 1, total_riders, cell_fmt)

            ws.set_column(0, 0, 24)
            ws.set_column(1, 1, 12)

        # Hourly Patterns sheet — match original: station/month header, heatmap + Total row, conditional format, two line charts
        hp_ws = workbook.add_worksheet("Hourly Patterns")
        hp_ws.freeze_panes(1, 1)
        month_label = pd.Timestamp(f"{month}-01").strftime("%B - %Y")
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        block_height = 40
        row_offset = 0
        for station_name in stations_to_export:
            daily = _daily_stats_for_station(df, month, station_name)
            if not daily:
                continue
            starts_df = daily["station_data"]["starts_df"]
            heat = _hourly_heatmap_for_station(starts_df)
            if heat.empty:
                continue
            r0 = row_offset
            hp_ws.write(r0, 0, f"{station_name} / {month_label}", label_fmt)
            r0 += 1
            hp_ws.write(r0, 0, "Day", header_fmt)
            for h in range(24):
                hp_ws.write(r0, h + 1, h, header_fmt)
            hp_ws.write(r0, 25, "Total", header_fmt)
            r0 += 1
            for day_name in day_names:
                hp_ws.write(r0, 0, day_name, label_fmt)
                for h in range(24):
                    try:
                        val = heat.loc[day_name, h] if day_name in heat.index and h in heat.columns else 0
                    except (KeyError, TypeError):
                        val = 0
                    hp_ws.write(r0, h + 1, int(val), cell_fmt)
                tot = int(heat.loc[day_name, "Total"]) if day_name in heat.index and "Total" in heat.columns else 0
                hp_ws.write(r0, 25, tot, cell_fmt)
                r0 += 1
            hp_ws.write(r0, 0, "Total", label_fmt)
            total_row_sums = 0
            for h in range(24):
                col_sum = sum(
                    int(heat.loc[d, h]) if d in heat.index and h in heat.columns else 0
                    for d in day_names
                )
                hp_ws.write(r0, h + 1, col_sum, cell_fmt)
                total_row_sums += col_sum
            hp_ws.write(r0, 25, total_row_sums, cell_fmt)
            hp_ws.conditional_format(
                row_offset + 2, 1, r0, 25,
                {"type": "3_color_scale", "min_color": "#F8696B", "mid_color": "#FFEB84", "max_color": "#63BE7B"}
            )
            r0 += 1
            data_row = r0 + 1
            hourly_totals = [
                sum(int(heat.loc[d, h]) if d in heat.index and h in heat.columns else 0 for d in day_names)
                for h in range(24)
            ]
            hp_ws.write(r0, 27, "Hour", label_fmt)
            hp_ws.write(r0, 28, "Rides", label_fmt)
            for h in range(24):
                hp_ws.write(data_row + h, 27, h, cell_fmt)
                hp_ws.write(data_row + h, 28, hourly_totals[h], cell_fmt)
            chart_hourly = workbook.add_chart({"type": "line"})
            chart_hourly.add_series({
                "categories": ["Hourly Patterns", data_row, 27, data_row + 23, 27],
                "values": ["Hourly Patterns", data_row, 28, data_row + 23, 28],
                "name": "Hourly trend",
                "data_labels": {"value": True},
            })
            chart_hourly.set_title({"name": "Hourly trend"})
            chart_hourly.set_x_axis({"name": "Hour"})
            chart_hourly.set_y_axis({"name": "Rides"})
            chart_hourly.set_size({"width": 480, "height": 240})
            hp_ws.insert_chart(r0 + 1, 0, chart_hourly)
            trend_df = compute_monthly_trend(STATIONS[station_name])
            hp_ws.write(r0, 30, "Month", label_fmt)
            hp_ws.write(r0, 31, "Start Rides", label_fmt)
            for i, row in trend_df.iterrows():
                hp_ws.write(data_row + i, 30, row["Month"], cell_fmt)
                hp_ws.write(data_row + i, 31, row["Start Rides"], cell_fmt)
            n_trend = len(trend_df)
            if n_trend > 0:
                chart_monthly = workbook.add_chart({"type": "line"})
                chart_monthly.add_series({
                    "categories": ["Hourly Patterns", data_row, 30, data_row + n_trend - 1, 30],
                    "values": ["Hourly Patterns", data_row, 31, data_row + n_trend - 1, 31],
                    "name": "Monthly trend",
                    "data_labels": {"value": True},
                })
                chart_monthly.set_title({"name": "Monthly trend"})
                chart_monthly.set_x_axis({"name": "Month"})
                chart_monthly.set_y_axis({"name": "Start Rides"})
                chart_monthly.set_size({"width": 400, "height": 240})
                hp_ws.insert_chart(r0 + 1, 10, chart_monthly)
            row_offset += block_height

    output.seek(0)
    return output.getvalue()


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
    
    # Year selector
    upload_year = st.selectbox(
        "Select Year", 
        AVAILABLE_YEARS, 
        key="upload_year_select",
        index=len(AVAILABLE_YEARS)-1  # Default to latest year
    )
    
    upload_months = get_months_for_year(upload_year)
    upload_month = st.selectbox("Select Month", upload_months, key="upload_month_select")
    
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
                year_dir = os.path.join(BASE_DATA_DIR, str(upload_year))
                path = os.path.join(year_dir, f"{upload_month}.{ext}")
                
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
    
    # Group by year
    for year in AVAILABLE_YEARS:
        uploaded = get_uploaded_months(year)
        
        if uploaded:
            st.markdown(f"**{year}**")
            for m in uploaded:
                col1, col2 = st.columns([3, 1])
                col1.markdown(f"✓ {m}")
                if col2.button("🗑️", key=f"del_{m}"):
                    year_from_month = m.split("-")[0]
                    for e in ["csv", "xlsx"]:
                        path = os.path.join(BASE_DATA_DIR, year_from_month, f"{m}.{e}")
                        if os.path.exists(path):
                            os.remove(path)
                    st.cache_data.clear()
                    st.rerun()
    
    if not get_uploaded_months():
        st.info("No data uploaded yet")

# ===============================
# MAIN HEADER
# ===============================
st.markdown("<h1 style='text-align: center; font-size: 48px; margin-bottom: 10px;'>🚇 Metro Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 18px; margin-bottom: 30px;'>Real-time Station Performance Insights</p>", unsafe_allow_html=True)

# ===============================
# MAIN CONTROLS
# ===============================
col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 1])

with col1:
    station = st.selectbox("🚉 Station", list(STATIONS.keys()), label_visibility="collapsed", placeholder="Select Station")

with col2:
    selected_year = st.selectbox("📆 Year", AVAILABLE_YEARS, label_visibility="collapsed", index=len(AVAILABLE_YEARS)-1)

with col3:
    available_months = get_months_for_year(selected_year)
    month = st.selectbox("📅 Month", available_months, label_visibility="collapsed", placeholder="Select Month")

with col4:
    show_comparison = st.checkbox("📊 Compare", value=True, help="Compare with previous month")

with col5:
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

st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
st.markdown("<div class='section-header'><p class='section-title'>📊 Monthly Excel Report</p></div>", unsafe_allow_html=True)

excel_bytes = export_month_to_excel(df, month)
st.download_button(
    label="📥 Download full month report (Excel)",
    data=excel_bytes,
    file_name=f"metro_report_{month}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
st.markdown("</div>", unsafe_allow_html=True)

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
    comparison_df = compute_station_comparison(df, month)
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
        csv_comp = export_to_csv(comparison_df, f"comparison_{month}.csv")
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
    chart_data = comparison_df.sort_values(metric_col, ascending=False)
    
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
        comparison_df.style.format({
            "Avg Duration": "{:.1f}",
            "Avg Rating": "{:.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )
    st.markdown("</div>", unsafe_allow_html=True)