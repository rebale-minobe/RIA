"""社会ページ"""
import streamlit as st
from shared.ui import render_subject_page

st.set_page_config(page_title="社会 - RIA", page_icon="🗺️", layout="wide")
render_subject_page("social", "社会", "🗺️")
