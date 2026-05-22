#import modules

import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
from pathlib import Path
import json
import os
from html import escape
import folium
from folium import Element
import altair as alt

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

# Farbschema
GENDER_COLORS = {
    "männlich": "#3182bd",
    "weiblich": "#e377c2",
    "unbekannt": "#969696",
}

PROFESSION_COLORS = {
    "wissenschaft": "#3B82F6",
    "kunst": "#F59E0B",
    "handwerk": "#B45309",
    "handel": "#8B5CF6",
    "religion": "#EC4899",
    "politik": "#DC2626",
    "adel": "#06B6D4",
    "militär": "#374151",
    "geografie": "#16A34A",
    "pflanzen": "#22C55E",
    "tiere": "#A16207",
    "gewässer": "#0EA5E9",
    "gebäude": "#78716C",
    "epoche": "#14B8A6",
    "sonstiges": "#9CA3AF",
    "Sonstiges": "#9CA3AF",
}

EPOCH_COLORS = {
    "Antike": "#8B5CF6",
    "Mittelalter": "#B45309",
    "Renaissance": "#F59E0B",
    "Barock": "#EC4899",
    "Klassizismus": "#3B82F6",
    "19. Jahrhundert": "#16A34A",
    "Moderne": "#DC2626",
    "keine Angabe": "#9CA3AF",
}

DEFAULT_STREET_COLOR = "#3B82F6"
INACTIVE_STREET_COLOR = "#D1D5DB"
UNKNOWN_STREET_COLOR = "#9CA3AF"


def _normalize_category(value: object) -> str:
    return str(value).strip().lower() if pd.notna(value) else ""


def _lookup_color(value: object, color_mapping: dict[str, str], default: str = UNKNOWN_STREET_COLOR) -> str:
    value_as_text = str(value).strip() if pd.notna(value) else ""
    if value_as_text in color_mapping:
        return color_mapping[value_as_text]

    normalized_mapping = {str(key).strip().lower(): color for key, color in color_mapping.items()}
    return normalized_mapping.get(value_as_text.lower(), default)


def _active_color_dimension(
    selected_geschlecht: list[str],
    selected_berufsgruppe: list[str],
    selected_epochen: list[str],
) -> str:
    """Bestimmt, nach welcher Dimension die Karte eingefärbt wird."""
    if selected_berufsgruppe:
        return "Berufsgruppe"
    if selected_epochen:
        return "Epoche"
    if selected_geschlecht:
        return "Geschlecht"
    return "Berufsgruppe"


def _color_for_row(row: pd.Series, color_dimension: str) -> str:
    if color_dimension == "Geschlecht":
        return _lookup_color(row.get("Geschlecht"), GENDER_COLORS)
    if color_dimension == "Epoche":
        return _lookup_color(row.get("Epoche"), EPOCH_COLORS)
    return _lookup_color(row.get("Berufsgruppe"), PROFESSION_COLORS, DEFAULT_STREET_COLOR)


def _legend_html(title: str, color_mapping: dict[str, str]) -> str:
    items = "".join(
        f"""
        <i class="fa fa-circle" style="color:{color}"></i>
        &nbsp; {escape(str(label))}<br>
        """
        for label, color in color_mapping.items()
    )

    return f"""
    <div style="
        position: fixed;
        bottom: 50px;
        right: 50px;
        width: 220px;
        padding: 10px;
        border: 2px solid grey;
        border-radius: 8px;
        z-index: 9999;
        font-size: 13px;
        background-color: white;
        opacity: 0.9;
        line-height: 1.6;
    ">
        &nbsp;<b>{escape(title)}</b><br><br>
        {items}
    </div>
    """


def add_map_legend(street_map: folium.Map, color_dimension: str) -> None:
    if color_dimension == "Geschlecht":
        legend = _legend_html("Legende – Geschlecht", GENDER_COLORS)
    elif color_dimension == "Epoche":
        legend = _legend_html("Legende – Epochen", EPOCH_COLORS)
    else:
        legend = _legend_html("Legende", PROFESSION_COLORS)

    street_map.get_root().html.add_child(folium.Element(legend))
st.markdown(
    f"""
    <style>
    :root {{
        --streetlore-primary: {DEFAULT_STREET_COLOR};
        --streetlore-secondary: #F59E0B;
        --streetlore-accent: #EC4899;
        --streetlore-muted: {UNKNOWN_STREET_COLOR};
    }}

    .stApp {{
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    }}

    h1, h2, h3 {{
        color: #111827;
    }}

    [data-testid="stSidebar"] {{
        background-color: #f8fafc;
        border-right: 1px solid #e5e7eb;
    }}

    div[data-testid="stMetricValue"],
    .stCaption {{
        color: var(--streetlore-primary);
    }}

    
    </style>
    """,
    unsafe_allow_html=True,
)

def add_north_arrow(street_map: folium.Map) -> None:
    """Fügt den Nordpfeil aus dem Notebook zur Folium-Karte hinzu."""
    street_map.get_root().html.add_child(Element("""
    <div style="
        position: fixed;
        top: 80px;
        left: 20px;
        z-index:9999;
        font-size:30px;
        color: #111827;
        background-color: rgba(255, 255, 255, 0.85);
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid #d1d5db;
        text-align: center;
        line-height: 1.1;
    ">
    ↑<br>N
    </div>
    """))

#load data from notebook
APP_DIR = Path(__file__).resolve().parent
NOTEBOOK_PATH = APP_DIR / "StreetLore_Aufbereitung.ipynb"


@st.cache_data(show_spinner="Daten werden aus dem Notebook aktualisiert ...")
def load_data_from_notebook(notebook_mtime_ns: int) -> pd.DataFrame:
    
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))

    namespace: dict[str, object] = {
        "__name__": "__streetlore_notebook_loader__",
        "__file__": str(NOTEBOOK_PATH),
    }

   #relative Pfade berücksichtigen
    old_cwd = os.getcwd()
    os.chdir(APP_DIR)

    try:
        for cell_number, cell in enumerate(notebook["cells"], start=1):
            if cell.get("cell_type") != "code":
                continue

            source = "".join(cell.get("source", []))

            if not source.strip():
                continue

            exec(
                compile(source, f"{NOTEBOOK_PATH.name}:cell_{cell_number}", "exec"),
                namespace,
            )

           
            if "data.to_csv" in source:
                break

    finally:
        os.chdir(old_cwd)

    df = namespace["data"].copy()

    # rename_columns
    rename_columns = {
        "geschlecht": "Geschlecht",
        "berufsgruppe": "Berufsgruppe",
        "epoche": "Epoche",
        "erklaerung_komplett": "Erklärung_komplett",
    }

    df = df.rename(
        columns={old: new for old, new in rename_columns.items() if old in df.columns}
    )

    return df

    if "data" not in namespace:
        st.error("Im Notebook wurde kein DataFrame mit dem Namen `data` gefunden.")
        st.stop()

    df = namespace["data"]
    if not isinstance(df, pd.DataFrame):
        st.error("Die Variable `data` aus dem Notebook ist kein pandas DataFrame.")
        st.stop()

    df = df.copy()

    #columns umbenennen
    df = df.rename(
        columns={
            "geschlecht": "Geschlecht",
            "berufsgruppe": "Berufsgruppe",
            "epoche": "Epoche",
        }
    )

    required_columns = [
        "Strassenname",
        "Erklärung erste Zeile",
        "Erklärung zweite Zeile",
        "Geo Shape",
        "Geo Point",
        "Geschlecht",
        "Berufsgruppe",
        "Epoche",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error(f"In den Notebook-Daten fehlen diese Spalten: {missing_columns}")
        st.stop()

    # Falls Erklärung_komplett nicht existiert, aus den beiden Zeilen erzeugen.
    if "Erklärung_komplett" not in df.columns:
        z1 = df["Erklärung erste Zeile"].fillna("").astype(str)
        z2 = df["Erklärung zweite Zeile"].fillna("").astype(str)
        df["Erklärung_komplett"] = (z1 + " " + z2).str.strip()

    return df


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
    selected_geschlecht: list[str],
    selected_berufsgruppe: list[str],
    selected_epochen: list[str],
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
    color_dimension = _active_color_dimension(
        selected_geschlecht=selected_geschlecht,
        selected_berufsgruppe=selected_berufsgruppe,
        selected_epochen=selected_epochen,
    )

    for row_id, row in df_all.iterrows():
        lines = _geo_shape_to_lines(row.get("Geo Shape"))
        if not lines:
            continue

        is_match = row_id in filtered_ids
        kategorie = str(row.get(farb_spalte, "")).lower() 
        base_color = farb_zuordnung.get(kategorie, "#999999")

        if filters_are_active:
            color = _color_for_row(row, color_dimension) if is_match else INACTIVE_STREET_COLOR
            weight = 5 if is_match else 1.5
            opacity = 0.95 if is_match else 0.22
        else:
            color = _color_for_row(row, color_dimension)
            weight = 3
            opacity = 0.82

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

    add_map_legend(street_map, color_dimension)
    add_north_arrow(street_map)
    return street_map

# title and description
st.title("StreetLore Basel - Die Geschichte hinter jedem Strassenschild")
st.write("""Wer war Elisabethen? Woher kommt der Name Spalentor?
         Basel erzählt seine Geschichte auf jedem Strassenschild, man muss nur genauer hinschauen. 
         StreetLore Basel macht diese versteckten Geschichten sichtbar: Erkunde auf einer interaktiven Karte, 
         nach wem und was Basels Strassen benannt sind, entdecke Muster zwischen Quartieren und tauche ein in die Geschichte deiner Stadt.""")


#data loading
df = load_data_from_notebook(NOTEBOOK_PATH.stat().st_mtime_ns)

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
        chart = (
            alt.Chart(statistik_df)
            .mark_bar()
            .encode(
                x=alt.X("Berufsgruppe:N", sort="-y", title="Berufsgruppe"),
                y=alt.Y("Anzahl:Q", title="Anzahl"),
                color=alt.Color(
                    "Berufsgruppe:N",
                    scale=alt.Scale(
                        domain=list(PROFESSION_COLORS.keys()),
                        range=list(PROFESSION_COLORS.values()),
                    ),
                    legend=None,
                ),
                tooltip=["Berufsgruppe", "Anzahl"],
            )
        )
        st.altair_chart(chart, use_container_width=True)

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

    color_dimension = _active_color_dimension(
        selected_geschlecht=selected_geschlecht,
        selected_berufsgruppe=selected_berufsgruppe,
        selected_epochen=selected_epochen,
    )
    
    
    street_map = build_street_map(
        df_all=df,
        df_filtered=filtered_df,
        filters_are_active=filters_are_active,
        selected_geschlecht=selected_geschlecht,
        selected_berufsgruppe=selected_berufsgruppe,
        selected_epochen=selected_epochen,
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
            background-color: #f8fafc;
            padding: 10px;
            text-align: center;
            font-size: 12px;
            color: #6b7280;
        }
    </style>
    <div class="footer">
        © 2026 StreetLore Basel · Daten: Kanton Basel-Stadt · 
        Erstellt von Best Hääckers · 
        <a href="mailto:kontakt@streetlore.ch">Kontakt</a>
    </div>
""", unsafe_allow_html=True)
    
