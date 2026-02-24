import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import io
import os
import json
import urllib.parse
from fpdf import FPDF
from datetime import datetime, date

# --- 1. SAMBUNGAN GOOGLE SHEETS ---
# Pastikan anda telah setup 'Secrets' di Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, columns):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame(columns=columns)

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

# --- 2. KESELAMATAN & SETTINGS ---
USER_CREDENTIALS = {"admin": "cikgu123", "staf": "skbn2025"}

def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Log Masuk Sistem SKBN Online")
        u = st.text_input("Nama Pengguna")
        p = st.text_input("Kata Laluan", type="password")
        if st.button("Masuk"):
            if u in USER_CREDENTIALS and p == USER_CREDENTIALS[u]:
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Kredential Salah")
        return False
    return True

# --- 3. PENJANA PDF ---
class PDF(FPDF):
    def header(self):
        settings = load_data("Settings", ["Key", "Value"])
        school_name = settings[settings['Key'] == 'school_name']['Value'].values[0] if not settings.empty else "SK BATU NIAH"
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, school_name, ln=True, align='C')
        self.line(10, 25, 200, 25)
        self.ln(10)

# --- 4. UI UTAMA ---
st.set_page_config(page_title="Sistem SKBN Online", layout="wide")

if check_password():
    # Load Semua Data dari Google Sheets
    df_asrama = load_data("Data_Asrama", ["Nama", "Kelas", "No. KP", "Bangsa", "Agama"])
    df_kehadiran = load_data("Rekod_Kehadiran", ["Tarikh", "Nama", "Hadir", "Sebab"])
    df_inventori = load_data("Inventori", ["Barang", "Kuantiti", "Status"])
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Daftar", "🏠 Asrama", "📅 Kehadiran", "📦 Inventori", "⚙️ Tetapan"])

    with tab1:
        st.subheader("Pendaftaran Pelajar")
        file = st.file_uploader("Upload Excel Pelajar", type=["xlsx"])
        if file:
            raw_df = pd.read_excel(file)
            st.dataframe(raw_df.head(5))
            sel_idx = st.selectbox("Pilih Pelajar:", raw_df.index, format_func=lambda x: str(raw_df.loc[x, raw_df.columns[0]]))
            if st.button("Daftar ke Google Sheets"):
                new_row = raw_df.loc[[sel_idx]]
                df_asrama = pd.concat([df_asrama, new_row]).drop_duplicates()
                save_data(df_asrama, "Data_Asrama")
                st.success("Telah disimpan ke Google Sheets!")

    with tab3:
        st.subheader("Kehadiran Harian")
        sel_date = st.date_input("Tarikh", value=date.today())
        if not df_asrama.empty:
            with st.form("att_form"):
                updates = []
                for _, r in df_asrama.iterrows():
                    c1, c2 = st.columns([3, 1])
                    h = c2.checkbox("Hadir", value=True, key=f"h_{r.name}")
                    updates.append({"Tarikh": str(sel_date), "Nama": r['Nama'], "Hadir": 1 if h else 0})
                if st.form_submit_button("Hantar Kehadiran"):
                    new_att = pd.DataFrame(updates)
                    df_kehadiran = pd.concat([df_kehadiran, new_att])
                    save_data(df_kehadiran, "Rekod_Kehadiran")
                    st.success("Kehadiran dikemaskini di Google Sheets!")

    with tab5:
        st.subheader("Tetapan Sekolah")
        s_name = st.text_input("Nama Sekolah", value="SEKOLAH KEBANGSAAN BATU NIAH")
        if st.button("Simpan Tetapan"):
            set_df = pd.DataFrame([{"Key": "school_name", "Value": s_name}])
            save_data(set_df, "Settings")
            st.success("Tetapan disimpan!")
