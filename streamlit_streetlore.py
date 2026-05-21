import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components


# title and description
st.title("StreetLore Basel - Die Geschichte hinter jedem Strassenschild")
st.write("""Wer war Elisabethen? Woher kommt der Name Spalentor?
         Basel erzählt seine Geschichte auf jedem Strassenschild, man muss nur genauer hinschauen. 
         StreetLore Basel macht diese versteckten Geschichten sichtbar: Erkunde auf einer interaktiven Karte, 
         nach wem und was Basels Strassen benannt sind, entdecke Muster zwischen Quartieren und tauche ein in die Geschichte deiner Stadt.""")


# logo
st.logo("logo_streetlore.png", size="large")

# dual button
control_button = st.segmented_control("", ["Karte", "Statistik"])

# map
if control_button == "Karte":
    with open("data/streetlore_map.html", "r", encoding="utf-8") as f:
        karte_html = f.read()
    components.html(karte_html, height=600, scrolling=True)

#stats

