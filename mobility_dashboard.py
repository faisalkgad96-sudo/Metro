import streamlit as st
import pandas as pd
import plotly.express as px
from math import radians, sin, cos, sqrt, atan2

# ------------------- HELPER FUNCTION -------------------
def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance (meters) between two coordinates."""
    R = 6371000
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

# ------------------- METRO COORDINATES -------------------
metro_stations = {
    "Heliopolis": (30.0908, 31.3196),
    "Koleyat El Banat": (30.0743, 31.3241),
    "Al Ahram": (30.0825, 31.3167),
    "Alf Maskan": (30.1108, 31.3387),
    "Haroun": (30.0853, 31.3271),
}
DISTANCE_THRESHOLD = 1000  # meters (1 km)

# ------------------- STREAMLIT SETUP -------------------
st.set_page_config(page_title="Masr El Gdeida Metro Dashboard", layout="wide")
st.title("🚲 Masr El Gdeida — Metro Station Ride Performance Dashboard")

uploaded_file = st.file_uploader("Upload your monthly dataset (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    # ---------- Load ----------
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # ---------- Clean ----------
    df["Start Date Local"] = pd.to_datetime(df["Start Date Local"], errors="coerce")
    df["End Date Local"]   = pd.to_datetime(df["End Date Local"],   errors="coerce")
    for col in ["Start Lat","Start Long","Stop Lat","Stop Long","Duration","Rating"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ---------- Assign nearest metro ----------
    def find_nearest_station(lat, lon):
        if pd.isna(lat) or pd.isna(lon):
            return None
        nearest_station, nearest_distance = None, float("inf")
        for name, (m_lat, m_lon) in metro_stations.items():
            dist = haversine(lat, lon, m_lat, m_lon)
            if dist < nearest_distance:
                nearest_station, nearest_distance = name, dist
        return nearest_station if nearest_distance <= DISTANCE_THRESHOLD else None

    st.info("Assigning rides to nearest metro station (≤ 1 km)… ⏳")
    df["Start Station"] = df.apply(lambda x: find_nearest_station(x["Start Lat"], x["Start Long"]), axis=1)
    df["End Station"]   = df.apply(lambda x: find_nearest_station(x["Stop Lat"],  x["Stop Long"]),  axis=1)

    # ---------- Remove non-metro rides completely ----------
    metro_names = list(metro_stations.keys())
    df = df[
        (df["Start Station"].isin(metro_names)) |
        (df["End Station"].isin(metro_names))
    ].copy()

    # Drop rows where both stations are None
    df = df.dropna(subset=["Start Station", "End Station"], how="all")

    # 🔥 Ensure no "Other" appears
    df = df[df["Start Station"].isin(metro_names + [None])]
    df = df[df["End Station"].isin(metro_names + [None])]

    st.success(f"✅ Filtered to {len(df):,} rides linked ONLY to the 5 metro stations.")

    # ------------------- STATION PERFORMANCE BREAKDOWN -------------------
    st.subheader("📊 Metro Station Performance Breakdown")

    # Groupings
    started = df.groupby("Start Station").size().rename("Rides Started")
    ended   = df.groupby("End Station").size().rename("Rides Ended")
    both    = df[df["Start Station"] == df["End Station"]].groupby("Start Station").size().rename("Rides Started & Ended")

    # Merge and clean
    station_summary = (
        pd.concat([started, ended, both], axis=1)
        .fillna(0).astype(int).reset_index()
        .rename(columns={"index": "Metro Station"})
    )

    # Only keep the 5 metro stations
    station_summary = station_summary[station_summary["Metro Station"].isin(metro_names)]

    station_summary["Total Related Rides"] = (
        station_summary["Rides Started"] + station_summary["Rides Ended"] - station_summary["Rides Started & Ended"]
    )

    # Color-coded dataframe
    def color_scale(val, series):
        max_val, min_val = series.max(), series.min()
        ratio = 0 if max_val == min_val else (val - min_val) / (max_val - min_val)
        r = int(255 * (1 - ratio)); g = int(255 * ratio)
        return f"background-color: rgb({r},{g},150,0.6)"

    styled_df = station_summary.style.apply(
        lambda s: [color_scale(v, s) if s.name in
                   ["Rides Started","Rides Ended","Rides Started & Ended","Total Related Rides"] else "" for v in s],
        axis=0
    )

    st.dataframe(styled_df, use_container_width=True)

    # ------------------- KPIs -------------------
    total_rides = len(df)
    total_users = df["User Id"].nunique()
    same_station_rides = df[df["Start Station"] == df["End Station"]].shape[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Metro Rides", f"{total_rides:,}")
    c2.metric("Unique Users", f"{total_users:,}")
    c3.metric("Same Metro Start & End", f"{same_station_rides:,}")
    st.markdown("---")

    # ------------------- BAR CHART -------------------
    melted = station_summary.melt(
        id_vars="Metro Station",
        value_vars=["Rides Started","Rides Ended","Rides Started & Ended"],
        var_name="Type", value_name="Rides"
    )
    fig_compare = px.bar(
        melted, x="Metro Station", y="Rides", color="Type",
        barmode="group", text_auto=True,
        title="Ride Breakdown per Metro Station (Start / End / Same)"
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    # ------------------- HOURLY TRENDS -------------------
    df["Hour"] = df["Start Date Local"].dt.hour
    df["Day Name"] = df["Start Date Local"].dt.day_name()
    df["Is Weekend"] = df["Day Name"].isin(["Friday","Saturday"])

    st.subheader("⏰ Hourly Usage Trends per Metro Station")
    hourly = df.groupby(["Start Station","Hour"]).size().reset_index(name="Rides")
    hourly = hourly[hourly["Start Station"].isin(metro_names)]
    fig_hour = px.line(hourly, x="Hour", y="Rides", color="Start Station",
                       markers=True, title="Hourly Ride Distribution by Metro Station")
    st.plotly_chart(fig_hour, use_container_width=True)

    # ------------------- WEEKDAY VS WEEKEND -------------------
    st.subheader("📅 Weekday vs Weekend Hourly Comparison")
    weekday = df[df["Is Weekend"]==False].groupby(["Start Station","Hour"]).size().reset_index(name="Rides")
    weekend = df[df["Is Weekend"]==True].groupby(["Start Station","Hour"]).size().reset_index(name="Rides")

    weekday = weekday[weekday["Start Station"].isin(metro_names)]
    weekend = weekend[weekend["Start Station"].isin(metro_names)]

    tab1, tab2 = st.tabs(["📆 Weekdays","🎉 Weekends"])
    with tab1:
        fig_wd = px.line(weekday, x="Hour", y="Rides", color="Start Station",
                         markers=True, title="Weekday Hourly Ride Trends")
        st.plotly_chart(fig_wd, use_container_width=True)
    with tab2:
        fig_we = px.line(weekend, x="Hour", y="Rides", color="Start Station",
                         markers=True, title="Weekend Hourly Ride Trends")
        st.plotly_chart(fig_we, use_container_width=True)

    # ------------------- MAP -------------------
    fig_map = px.scatter_mapbox(
        df[df["Start Station"].isin(metro_names)],
        lat="Start Lat", lon="Start Long", color="Start Station",
        zoom=12, mapbox_style="carto-positron",
        title="Ride Start Locations Colored by Nearest Metro Station"
    )
    st.plotly_chart(fig_map, use_container_width=True)

    st.success("✅ Metro analysis completed — 'Other' removed completely!")
