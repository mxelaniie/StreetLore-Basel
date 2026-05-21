import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components

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

# title and description
st.title("StreetLore Basel - Die Geschichte hinter jedem Strassenschild")
st.write("""Wer war Elisabethen? Woher kommt der Name Spalentor?
         Basel erzählt seine Geschichte auf jedem Strassenschild, man muss nur genauer hinschauen. 
         StreetLore Basel macht diese versteckten Geschichten sichtbar: Erkunde auf einer interaktiven Karte, 
         nach wem und was Basels Strassen benannt sind, entdecke Muster zwischen Quartieren und tauche ein in die Geschichte deiner Stadt.""")


# dual button
control_button = st.segmented_control("", ["Karte", "Statistik"])

#dataframe
df = pd.DataFrame({
    "Kategorie": ["Personen", "Orte", "Ereignisse", "Sonstiges"],
    "Prozentsatz": [40, 30, 20, 10]
})

#stats
if control_button == "Statistik":
    st.subheader("Verteilung der Strassennamen nach Kategorien")
    st.bar_chart(df, x="Kategorie", y="Prozentsatz")
    
 # map
else:
    st.subheader("Entdecke die Geschichten hinter den Strassennamen auf der Karte")
    with open("data/streetlore_gender_map.html", "r", encoding="utf-8") as f:
        karte_html = f.read()
    components.html(karte_html, height=600, scrolling=True)
    
    
#sidebar and filters
def reset_filters():
    st.session_state["geschlecht"] = []
    st.session_state["berufsbezug"] = []
    st.session_state["epochen"] = []
    st.session_state["kategorie"] = []

with st.sidebar:
    st.subheader("Filter")
    options = st.multiselect(
        "Geschlecht",
        ["männlich", "weiblich", "neutral"],
        key="geschlecht"
    )

    options2 = st.multiselect(
        "Berufsbezug",
        ["Wissenschaft", "Kunst", "Handwerk", "Handel", "Politik", "Adel", "Militär"],
        key="berufsbezug"
    )

    options3 = st.multiselect(
        "Epochen",
        ["Mittelalter", "Renaissance", "Barock", "Klassizismus", "19. Jahrhundert", "Moderne", "zeitgenössisch"],
        key="epochen"
    )

    options4 = st.multiselect(
        "Kategorie",
        ["Geografie", "Gebäude", "Personen"],
        key="kategorie"
    )

    st.button("Filter zurücksetzen", on_click=reset_filters)
    


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
    
