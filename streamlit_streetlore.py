#import modules

import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
from pathlib import Path
import json
from html import escape
import folium
from classify import classify_epoch, classify_profession, classify_gender

# Farbschema
FARBEN_GESCHLECHT = {
    'männlich':  '#3182bd',   # Blau
    'weiblich':  '#e377c2',   # Rosa
    'unbekannt': '#969696',   # Grau
}

FARBEN_BERUFSGRUPPE = {
    'wissenschaft': '#3B82F6',
    'kunst':        '#F59E0B',
    'handwerk':     '#B45309',
    'handel':       '#8B5CF6',
    'religion':     '#EC4899',
    'politik':      '#DC2626',
    'adel':         '#06B6D4',
    'militär':      '#374151',
    'geografie':    '#16A34A',
    'pflanzen':     '#22C55E',
    'tiere':        '#A16207',
    'gewässer':     '#0EA5E9',
    'gebäude':      '#78716C',
    'epoche':       '#14B8A6',
    'Sonstiges':    '#9CA3AF',
}
FARBEN_EPOCHEN = {
    "antike": "#8B5CF6",
    "mittelalter": "#B45309",
    "renaissance": "#F59E0B",
    "barock": "#EC4899",
    "klassizismus": "#3B82F6",
    "19. Jahrhundert": "#16A34A",
    "moderne": "#DC2626",
    "keine Angabe": "#9CA3AF"
}
#website configuration
st.set_page_config(
    page_title="StreetLore Basel",
    page_icon="data/logo_streetlore.png",
    layout="wide"
)

# logo
st.logo("data/logo_streetlore.png")

st.markdown(
    """
    <style>
    [alt=Logo] {
        height: 4.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

#load data
@st.cache_data
def load_and_classify_data() -> pd.DataFrame:
    
    csv_path = "data/CSV_fuer_Streamlint.csv"

    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8")
    except FileNotFoundError:
        st.error(
            "CSV-Datei nicht gefunden. Lege die Datei "
            "'CSV_fuer_Streamlint.csv' in den Ordner data ab."
        )
        st.stop()

    required_columns = ["Strassenname", "Erklärung erste Zeile", "Erklärung zweite Zeile"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error(f"In der CSV fehlen diese Spalten: {missing_columns}")
        st.stop()

    def get_explanation(row: pd.Series) -> str:
        z1 = "" if pd.isna(row.get("Erklärung erste Zeile")) else str(row.get("Erklärung erste Zeile"))
        z2 = "" if pd.isna(row.get("Erklärung zweite Zeile")) else str(row.get("Erklärung zweite Zeile"))
        return f"{z1} {z2}".strip()

    df["_explanation"] = df.apply(get_explanation, axis=1)

#classify data from classify.py
    df["Geschlecht"] = df.apply(
        lambda row: classify_gender(row["Strassenname"], row["_explanation"]),
        axis=1,
    )

    df["Berufsgruppe"] = df.apply(
        lambda row: classify_profession(row["Strassenname"], row["_explanation"]),
        axis=1,
    )

    df["Epoche"] = df.apply(
        lambda row: classify_epoch(
            row["Strassenname"],
            row["_explanation"],
            erstmals_erwaehnt=row.get("Erstmals erwähnt"),
            amtlich_benannt=row.get("Amtlich benannt"),
        ),
        axis=1,
    )

# Falls Erklärung_komplett nicht existiert, aus den beiden Zeilen erzeugen
    if "Erklärung_komplett" not in df.columns:
        df["Erklärung_komplett"] = df["_explanation"]

    return df.drop(columns=["_explanation"])

#def filters
def has_active_filters(
    selected_geschlecht: list[str],
    selected_berufsgruppe: list[str],
    selected_epochen: list[str],
) -> bool:
   #check if any filter is active
    return bool(selected_geschlecht or selected_berufsgruppe or selected_epochen)

#change coordinates from json to tuples
def _geo_shape_to_lines(geo_shape: object) -> list[list[tuple[float, float]]]:
    
    if pd.isna(geo_shape):
        return []

    try:
        geometry = json.loads(str(geo_shape))
    except (TypeError, json.JSONDecodeError):
        return []

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "LineString":
        return [[(lat, lon) for lon, lat in coordinates]]

    if geometry_type == "MultiLineString":
        return [
            [(lat, lon) for lon, lat in line]
            for line in coordinates
            if line
        ]

    return []


#folium map
def _get_map_center(df: pd.DataFrame) -> tuple[float, float]:
   #center of the map in Basel
    if "Geo Point" not in df.columns:
        return 47.5596, 7.5886

    points = df["Geo Point"].dropna().astype(str).str.split(",", expand=True)
    if points.shape[1] < 2:
        return 47.5596, 7.5886

    lat = pd.to_numeric(points[0].str.strip(), errors="coerce")
    lon = pd.to_numeric(points[1].str.strip(), errors="coerce")

    if lat.dropna().empty or lon.dropna().empty:
        return 47.5596, 7.5886

    return float(lat.mean()), float(lon.mean())


def build_street_map(
    df_all: pd.DataFrame,
    df_filtered: pd.DataFrame,
    filters_are_active: bool,
    farb_modus: str = "geschlecht",
) -> folium.Map:
    
    # Farbschema wählen
    if farb_modus == "geschlecht":
        farb_zuordnung = FARBEN_GESCHLECHT
        farb_spalte = "Geschlecht"
    elif farb_modus == "epoche":
        farb_zuordnung = FARBEN_EPOCHEN
        farb_spalte = "Epoche"
    else:
        farb_zuordnung = FARBEN_BERUFSGRUPPE
        farb_spalte = "Berufsgruppe"
    
    center_lat, center_lon = _get_map_center(df_all)

    street_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles="CartoDB positron",
        control_scale=True,
    )

    filtered_ids = set(df_filtered.index)

    for row_id, row in df_all.iterrows():
        lines = _geo_shape_to_lines(row.get("Geo Shape"))
        if not lines:
            continue

        is_match = row_id in filtered_ids
        kategorie = str(row.get(farb_spalte, "")).lower() 
        base_color = farb_zuordnung.get(kategorie, "#999999")

        if filters_are_active:
            color = base_color if is_match else "#bdbdbd"
            weight = 5 if is_match else 1.5
            opacity = 0.95 if is_match else 0.25
        else:
            color = base_color
            weight = 3
            opacity = 0.75

        popup_html = f"""
        <b>{escape(str(row.get('Strassenname', 'Unbekannte Strasse')))}</b><br>
        Geschlecht: {escape(str(row.get('Geschlecht', '')))}<br>
        Berufsgruppe: {escape(str(row.get('Berufsgruppe', '')))}<br>
        Epoche: {escape(str(row.get('Epoche', '')))}
        """

        for line in lines:
            folium.PolyLine(
                locations=line,
                color=color,
                weight=weight,
                opacity=opacity,
                popup=folium.Popup(popup_html, max_width=350),
            ).add_to(street_map)

    return street_map

# title and description
st.title("StreetLore Basel - Die Geschichte hinter jedem Strassenschild")
st.write("""Wer war Elisabethen? Woher kommt der Name Spalentor?
         Basel erzählt seine Geschichte auf jedem Strassenschild, man muss nur genauer hinschauen. 
         StreetLore Basel macht diese versteckten Geschichten sichtbar: Erkunde auf einer interaktiven Karte, 
         nach wem und was Basels Strassen benannt sind, entdecke Muster zwischen Quartieren und tauche ein in die Geschichte deiner Stadt.""")


#data loading
df = load_and_classify_data()

def reset_filters() -> None:
    st.session_state["geschlecht"] = []
    st.session_state["berufsgruppe"] = []
    st.session_state["epochen"] = []


def apply_filters(
    df: pd.DataFrame,
    selected_geschlecht: list[str],
    selected_berufsgruppe: list[str],
    selected_epochen: list[str],
) -> pd.DataFrame:
    """Filter aus den Multiselects auf das DataFrame anwenden."""
    filtered_df = df.copy()

    if selected_geschlecht:
        filtered_df = filtered_df[filtered_df["Geschlecht"].isin(selected_geschlecht)]

    if selected_berufsgruppe:
        filtered_df = filtered_df[filtered_df["Berufsgruppe"].isin(selected_berufsgruppe)]

    if selected_epochen:
        filtered_df = filtered_df[filtered_df["Epoche"].isin(selected_epochen)]

    return filtered_df


# Daten laden
df = load_and_classify_data()


# sidebar and filters
with st.sidebar:
    st.subheader("Filter")

    geschlecht_options = sorted(df["Geschlecht"].dropna().unique())
    berufsgruppe_options = sorted(df["Berufsgruppe"].dropna().unique())
    epochen_options = sorted(df["Epoche"].dropna().unique())

    selected_geschlecht = st.multiselect(
        "Geschlecht",
        options=geschlecht_options,
        key="geschlecht",
    )

    selected_berufsgruppe = st.multiselect(
        "Berufsgruppe / Kategorie",
        options=berufsgruppe_options,
        key="berufsgruppe",
    )

    selected_epochen = st.multiselect(
        "Epochen",
        options=epochen_options,
        key="epochen",
    )

    st.button("Filter zurücksetzen", on_click=reset_filters)

filtered_df = apply_filters(
    df=df,
    selected_geschlecht=selected_geschlecht,
    selected_berufsgruppe=selected_berufsgruppe,
    selected_epochen=selected_epochen,
)

filters_are_active = has_active_filters(
    selected_geschlecht=selected_geschlecht,
    selected_berufsgruppe=selected_berufsgruppe,
    selected_epochen=selected_epochen,
)

if selected_geschlecht and not selected_berufsgruppe and not selected_epochen:
    farb_modus = "geschlecht"
elif selected_epochen and not selected_geschlecht and not selected_berufsgruppe:
    farb_modus = "epoche"
else:
    farb_modus = "berufsgruppe"


#dual button
control_button = st.segmented_control("", ["Karte", "Statistik"], default="Karte")

st.caption(f"Anzahl Strassen nach aktuellem Filter: {len(filtered_df)} von {len(df)}")

#stats
if control_button == "Statistik":
    st.subheader("Verteilung der Strassennamen nach Berufsgruppen / Kategorien")

    statistik_df = (
        filtered_df["Berufsgruppe"]
        .value_counts()
        .reset_index()
    )
    statistik_df.columns = ["Berufsgruppe", "Anzahl"]

    if statistik_df.empty:
        st.info("Für die aktuelle Filterauswahl gibt es keine Treffer.")
    else:
        st.bar_chart(statistik_df, x="Berufsgruppe", y="Anzahl")

    st.subheader("Gefilterte Daten")

    display_columns = [
        col
        for col in [
            "Strassenname",
            "Geschlecht",
            "Berufsgruppe",
            "Epoche",
            "Erklärung_komplett",
            "Erstmals erwähnt",
            "Amtlich benannt",
        ]
        if col in filtered_df.columns
    ]

    st.dataframe(filtered_df[display_columns], use_container_width=True)

#map
else:
    st.subheader("Entdecke die Geschichten hinter den Strassennamen auf der Karte")
    
    street_map = build_street_map(
        df_all=df,
        df_filtered=filtered_df,
        filters_are_active=filters_are_active,
        farb_modus=farb_modus
    )
    components.html(street_map._repr_html_(), height=650, scrolling=False)


#footer
st.markdown("""
    <style>
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: #f0f0f0;
            padding: 10px;
            text-align: center;
            font-size: 12px;
            color: #888;
        }
    </style>
    <div class="footer">
        © 2026 StreetLore Basel · Daten: Kanton Basel-Stadt · 
        Erstellt von Best Hääckers · 
        <a href="mailto:kontakt@streetlore.ch">Kontakt</a>
    </div>
""", unsafe_allow_html=True)
    
