#import modules
import streamlit as st
import pandas as pd
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

# Definition Farbschema
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
    "sonstiges": "#9CA3AF",
}

EPOCH_COLORS = {
    "antike": "#8B5CF6",
    "mittelalter": "#B45309",
    "renaissance": "#F59E0B",
    "barock": "#EC4899",
    "klassizismus": "#3B82F6",
    "19. Jahrhundert": "#16A34A",
    "Moderne": "#DC2626",
    "keine Angabe": "#9CA3AF",
}

DEFAULT_STREET_COLOR = "#3B82F6"
INACTIVE_STREET_COLOR = "#D1D5DB"
UNKNOWN_STREET_COLOR = "#9CA3AF"


def get_color(value, color_dict, default=UNKNOWN_STREET_COLOR):
    return color_dict.get(str(value).strip().lower(), default)


def get_color_dimension() -> str:
    if selected_berufsgruppe:
        return "Berufsgruppe"
    elif selected_epochen:
        return "Epoche"
    elif selected_geschlecht:
        return "Geschlecht"
    else:
        return "Berufsgruppe"


def get_street_color(row: pd.Series, color_dimension: str) -> str:
    if color_dimension == "Geschlecht":
        return get_color(row["Geschlecht"], GENDER_COLORS)

    if color_dimension == "Epoche":
        return get_color(row["Epoche"], EPOCH_COLORS)

    return get_color(row["Berufsgruppe"], PROFESSION_COLORS, DEFAULT_STREET_COLOR)

def _legend_section(title: str, color_mapping: dict[str, str]) -> str:
    items = "".join(
        f"""
        <i class="fa fa-circle" style="color:{color}"></i>
        &nbsp; {escape(str(label))}<br>
        """
        for label, color in color_mapping.items()
    )

    return f"""
    <b>{escape(title)}</b><br>
    {items}
    <br>
    """


def add_map_legend(street_map: folium.Map) -> None:
    legend = f"""
    <div style="
        position: fixed;
        bottom: 50px;
        right: 50px;
        width: 260px;
        max-height: 420px;
        overflow-y: auto;
        padding: 10px;
        border: 2px solid grey;
        border-radius: 8px;
        z-index: 9999;
        font-size: 13px;
        background-color: white;
        opacity: 0.9;
        line-height: 1.6;
    ">
        <b>Legende</b><br><br>
        {_legend_section("Geschlecht", GENDER_COLORS)}
        {_legend_section("Berufsgruppe / Kategorie", PROFESSION_COLORS)}
        {_legend_section("Epoche", EPOCH_COLORS)}
    </div>
    """
   
    street_map.get_root().html.add_child(folium.Element(legend))

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
    "geo_shape": "Geo Shape",
    "geo_point": "Geo Point",
}

    df = df.rename(
        columns={old: new for old, new in rename_columns.items() if old in df.columns}
    )

    return df


#change coordinates from json to tuples
def _geo_shape_to_lines(geo_shape: object) -> list[list[tuple[float, float]]]:
    if geo_shape is None or pd.isna(geo_shape):
        return []

    if isinstance(geo_shape, dict):
        geometry = geo_shape
    else:
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

def build_street_map(df_map: pd.DataFrame, color_dimension: str) -> folium.Map:
    street_map = folium.Map(
        location=[47.5596, 7.5886],
        zoom_start=13,
        tiles="CartoDB positron",
        control_scale=True,
    )

    for _, row in df_map.iterrows():
        for line in _geo_shape_to_lines(row.get("Geo Shape")):
            folium.PolyLine(
                locations=line,
                color=get_street_color(row, color_dimension),
                weight=4,
                opacity=0.85,
                popup=folium.Popup(
                    f"""
                    <b>{escape(str(row.get('Strassenname', 'Unbekannte Strasse')))}</b><br>
                    Geschlecht: {escape(str(row.get('Geschlecht', '')))}<br>
                    Berufsgruppe: {escape(str(row.get('Berufsgruppe', '')))}<br>
                    Epoche: {escape(str(row.get('Epoche', '')))}
                    """,
                    max_width=350,
                ),
            ).add_to(street_map)

    add_map_legend(street_map)
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

filters_are_active = bool(
    selected_geschlecht or selected_berufsgruppe or selected_epochen
)

#dual button
control_button = st.segmented_control("", ["Karte", "Statistik"], default="Karte")

st.caption(f"Anzahl Strassen nach aktuellem Filter: {len(filtered_df)} von {len(df)}")

#stats
if control_button == "Statistik":
    st.subheader("Verteilung der Strassennamen nach Geschlecht")
    statistik_Geschlecht = df["Geschlecht"].value_counts().reset_index(name="Anzahl")
    st.bar_chart(statistik_Geschlecht, x="Geschlecht", y="Anzahl", color= "#46bd31")

    st.subheader("Verteilung der Strassennamen nach Berufsgruppe / Kategorie")
    statistik_Berufsgruppe = df["Berufsgruppe"].value_counts().reset_index(name="Anzahl")
    st.bar_chart(statistik_Berufsgruppe, x="Berufsgruppe", y="Anzahl", color="#824B9D")

    st.subheader("Verteilung der Strassennamen nach Epochen")
    statistik_Epochen = df["Epoche"].value_counts().reset_index(name="Anzahl")
    st.bar_chart(statistik_Epochen, x="Epoche", y="Anzahl", color="#6A65D3")
#map
else:
    st.subheader("Entdecke die Geschichten hinter den Strassennamen auf der Karte")

    street_map = build_street_map(
    df_map=filtered_df,
    color_dimension=get_color_dimension(),
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
    
