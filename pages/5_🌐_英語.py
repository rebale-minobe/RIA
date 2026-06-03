"""英語ページ"""
import streamlit as st
from shared.ui import render_subject_page

st.set_page_config(page_title="英語 - RIA", page_icon="🌐", layout="wide")
render_subject_page("english", "英語", "🌐")
