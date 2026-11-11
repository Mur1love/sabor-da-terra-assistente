"""Tela mínima para validar o ambiente (a interface conversacional vem na etapa 13)."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Sabor da Terra — Assistente", page_icon="🌱")
st.title("Sabor da Terra — Assistente")
st.write("Ambiente pronto. A interface conversacional chega na etapa 13.")
