from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from classify import classify_epoch, classify_gender, classify_profession


# -----------------------------------------------------------------------------
# Website configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="StreetLore Basel",
    page_icon="data/logo_streetlore.png",
    layout="wide",
)

# Logo, falls vorhanden
logo_path = Path("data/logo_streetlore.png")
if logo_path.exists():
    st.logo(str(logo_path))

st.markdown(
    """
    <style>
    [alt=Logo] {
        height: 4.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Hilfsfunktionen
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_classify_data() -> pd.DataFrame:
    """CSV laden und mit den Funktionen aus classify.py klassifizieren."""
    base_dir = Path(__file__).parent

    # Passe diesen Dateinamen an, falls deine CSV anders heisst oder in /data liegt.
    possible_csv_paths = [
        base_dir / "CSV_fuer_Streamlint.csv",
        base_dir / "data" / "CSV_fuer_Streamlint.csv",
        base_dir / "100189_raw.csv",
        base_dir / "data" / "100189_raw.csv",
    ]

    csv_path = next((path for path in possible_csv_paths if path.exists()), None)
    if csv_path is None:
        st.error(
            "CSV-Datei nicht gefunden. Lege die CSV z.B. als "
            "'CSV_fuer_Streamlint.csv' in denselben Ordner wie diese Streamlit-Datei."
        )
        st.stop()

    df = pd.read_csv(csv_path, sep=";", encoding="utf-8")

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

    # Klassifizierungen aus classify.py anwenden
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


# -----------------------------------------------------------------------------
# Titel und Intro
# -----------------------------------------------------------------------------
st.title("StreetLore Basel - Die Geschichte hinter jedem Strassenschild")
st.write(
    """Wer war Elisabethen? Woher kommt der Name Spalentor?
    Basel erzählt seine Geschichte auf jedem Strassenschild, man muss nur genauer hinschauen.
    StreetLore Basel macht diese versteckten Geschichten sichtbar: Erkunde auf einer interaktiven Karte,
    nach wem und was Basels Strassen benannt sind, entdecke Muster zwischen Quartieren und tauche ein in die Geschichte deiner Stadt."""
)

# Daten laden
df = load_and_classify_data()


# -----------------------------------------------------------------------------
# Sidebar mit Multiselect-Filtern
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Inhalt: Karte oder Statistik
# -----------------------------------------------------------------------------
control_button = st.segmented_control("", ["Karte", "Statistik"], default="Karte")

st.caption(f"Anzahl Strassen nach aktuellem Filter: {len(filtered_df)} von {len(df)}")

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

else:
    st.subheader("Entdecke die Geschichten hinter den Strassennamen auf der Karte")

    # Hinweis: Die HTML-Karte ist statisch. Die Filter wirken hier auf die Tabelle darunter.
    # Für eine wirklich filterbare Karte müsste die Karte direkt aus filtered_df gebaut werden,
    # z.B. mit folium, pydeck oder st.map.
    map_path = Path("data/streetlore_gender_map.html")
    if map_path.exists():
        with open(map_path, "r", encoding="utf-8") as f:
            karte_html = f.read()
        components.html(karte_html, height=600, scrolling=True)
    else:
        st.warning("Die Datei 'data/streetlore_gender_map.html' wurde nicht gefunden.")

    st.subheader("Gefilterte Strassen")

    display_columns = [
        col
        for col in [
            "Strassenname",
            "Geschlecht",
            "Berufsgruppe",
            "Epoche",
            "Erklärung_komplett",
        ]
        if col in filtered_df.columns
    ]

    st.dataframe(filtered_df[display_columns], use_container_width=True)


# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown(
    """
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
    """,
    unsafe_allow_html=True,
)
