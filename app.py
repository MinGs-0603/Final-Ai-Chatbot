import streamlit as st

st.set_page_config(page_title="생산계획 통합 시스템", page_icon="🏭", layout="wide")

from legacy_chatbot import render_legacy_chatbot
from hybrid_ui import render_hybrid_system

st.title("🏭 생산계획 통합 시스템")

tab1, tab2 = st.tabs(["🏭 생산계획 보조 챗봇(조회)", "🤖 하이브리드 수사 시스템(조정)"])

with tab1:
    render_legacy_chatbot()

with tab2:
    render_hybrid_system()
