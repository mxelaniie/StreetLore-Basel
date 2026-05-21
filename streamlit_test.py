import streamlit as st
import pandas as pd
import numpy as np

st.title("Meine erste Webseite")
st.write("Hallo Welt")


map_data = pd.DataFrame(
    np.random.randn(1000, 2) / [50, 50] + [37.76, -122.4],
    columns=['lat', 'lon'])

st.map(map_data)


if st.checkbox('Show dataframe'):
    chart_data = pd.DataFrame(
       np.random.randn(20, 3),
       columns=['a', 'b', 'c'])

    chart_data

add_selectbox = st.sidebar.selectbox(
    "Wie wollen sie kontaktiert werden?", ("Email", "Telefon", "Brieftaube")
)


x = st.slider("x")
st.write(x, "quadriert ist", x * x)