import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import os
import openai

st.set_page_config(
    page_title="Arther",
    page_icon="👋",
)

st.write("# Welcome to Arther! 👋")

st.markdown(
    """
    Arther is your personalized Art Therapist!

    Write a journal entry, select your art style,
    and Arther will translate your thoughts into an 
    image that you can play with! 
    """
)

art_styles = ["",
              "Baroque",
              "Renaissance",
              "Gothic",
              "Rococo",
              "Neoclassicism",
              "Romanticism",
              "Realism",
              "Impressionism",
              "Post-Impressionism",
              "Art Nouveau",
              "Fauvism",
              "Expressionism",
              "Cubism",
              "Futurism",
              "Dada",
              "Surrealism",
              "Abstract Expressionism",
              "Pop Art",
              "Minimalism",
              "Conceptual Art",
              "Performance Art",
              "Installation Art",
              "Graffiti Art"
              ]

def journalStyleCallback():
    if st.session_state.journal and st.session_state.style:
      st.session_state["switch_page_from_home"] = True

jval = ''
if "journal" in st.session_state:
    jval = st.session_state.journal
sIdx = 0
if "style" in st.session_state:
    sIdx = art_styles.index(st.session_state.style)

journal = st.text_input('How are you feeling today?', value=jval, key="journal", on_change=journalStyleCallback)
style = st.selectbox("Select your art style", index=sIdx, options=art_styles, key="style", on_change=journalStyleCallback)
if "switch_page_from_home" in st.session_state and st.session_state["switch_page_from_home"]:
    switch_page("Display Arthers")
