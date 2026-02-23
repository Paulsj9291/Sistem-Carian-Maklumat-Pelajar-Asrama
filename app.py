import streamlit as st
import pandas as pd
import io
import os
import json
import urllib.parse
from fpdf import FPDF
from datetime import datetime, date
from PIL import Image

# --- 1. KONFIGURASI FAIL & KESELAMATAN ---
USER_CREDENTIALS = {"admin": "cikgu123", "staf": "skbn2025"}
FILES = {
    "asrama": "data_asrama.csv",
    "kehadiran": "data_kehadiran.csv",
    "cuti": "data_cuti.csv",
    "inventori": "data_inventori.csv",
    "settings": "settings.json"
}

# Inisialisasi fail jika belum wujud
for f_key, f_path in FILES.items():
    if not os.path.exists(f_path):
        if f_key == "settings":
            with open(f_path, 'w') as f:
                json.dump({
                    "school_name": "SEKOLAH KEBANGSAAN BATU NIAH",
                    "school_logo": None,
                    "staff": {}
                }, f)
        else:
            pd.DataFrame().to_csv(f_path, index=False)

def load_settings():
    with open(FILES["settings"], 'r') as f:
        return json.load(f)

def save_settings(s):
    with open(FILES["settings"], 'w') as f:
        json.dump(s, f)

def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Log Masuk Sistem SKBN v9.0")
        u = st.text_input("Nama Pengguna")
        p = st.text_input("Kata Laluan", type="password")
        if st.button("Masuk"):
            if u in USER_CREDENTIALS and p == USER_CREDENTIALS[u]:
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Kredential Salah")
        return False
    return True

# --- 2. FUNGSI PDF DINAMIK ---
class PDF(FPDF):
    def header(self):
        settings = load_settings()
        if settings.get("school_logo") and os.path.exists(settings["school_logo"]):
            self.image(settings["school_logo"], 10, 8, 20)
        
        self.set_font('Arial', 'B', 12)
        self.cell(30) # Space for logo
        self.cell(0, 5, settings.get("school_name", "NAMA SEKOLAH"), ln=True, align='L')
        self.set_font('Arial', '', 10)
        self.cell(30)
        self.cell(0, 5, 'D/A PEJABAT PENDIDIKAN DAERAH SUBIS', ln=True, align='L')
        self.cell(30)
        self.cell(0, 5, '98150 BEKENU, SARAWAK', ln=True, align='L')
        self.line(10, 32, 200, 32)
        self.ln(10)

def generate_offer_letter(row):
    settings = load_settings()
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 11)
    
    # Rujukan & Tarikh
    pdf.cell(0, 10, f"Ruj. Kami: SKBN.T.700-10/2/1 ({row.name})", ln=True, align='R')
    pdf.cell(0, 5, f"Tarikh: {datetime.now().strftime('%d %B %Y')}", ln=True, align='R')
    pdf.ln(5)
    
    # Nama Pelajar
    pdf.set_font('Arial', 'B', 11)
    nama_p = str(row.get('Nama', 'PELAJAR')).upper()
    pdf.cell(0, 5, nama_p, ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, "Niah, Sarawak.", ln=True)
    pdf.ln(10)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.multi_cell(0, 5, "TAWARAN MASUK KE ASRAMA BAGI SESI TAHUN 2025-2026")
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 11)
    text = f"Sukacita dimaklumkan bahawa anak jagaan tuan, {nama_p} telah ditawarkan menduduki asrama bagi sesi 2025."
    pdf.multi_cell(0, 6, text)
    pdf.ln(15)
    
    # Tandatangan Guru Besar Dinamik
    gb = settings["staff"].get("Guru Besar", {"nama": "....................", "gred": ""})
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, f"({gb['nama'].upper()})", ln=True)
    pdf.cell(0, 5, f"Guru Besar {gb.get('gred', '')}", ln=True)
    pdf.cell(0, 5, settings["school_name"], ln=True)
    
    return pdf.output()

# --- 3. UI APLIKASI ---
st.set_page_config(page_title="Sistem Pengurusan Pelajar Pro", layout="wide")

if check_password():
    settings = load_settings()
    data_asrama = pd.read_csv(FILES["asrama"])
    
    with st.sidebar:
        if settings.get("school_logo") and os.path.exists(settings["school_logo"]):
            st.image(settings["school_logo"], width=100)
        st.title(settings["school_name"])
        if st.button("🚪 Log Keluar"):
            st.session_state.clear()
            st.rerun()

    tabs = st.tabs(["🔍 Pendaftaran", "🏠 Maklumat Asrama", "📅 Kehadiran", "📦 Inventori", "⚙️ Tetapan"])

    # --- TAB TETAPAN (FUNGSI BARU) ---
    with tabs[4]:
        st.subheader("⚙️ Tetapan Sekolah & Pengurusan Staf")
        
        col_s1, col_s2 = st.columns(2)
        
        with col_s1:
            st.write("### 🏫 Maklumat Sekolah")
            new_name = st.text_input("Nama Sekolah", value=settings["school_name"])
            logo_file = st.file_uploader("Muat Naik Logo Sekolah (PNG/JPG)", type=["png", "jpg", "jpeg"])
            
            if st.button("Simpan Maklumat Sekolah"):
                settings["school_name"] = new_name
                if logo_file:
                    logo_path = f"logo_{logo_file.name}"
                    with open(logo_path, "wb") as f:
                        f.write(logo_file.getbuffer())
                    settings["school_logo"] = logo_path
                save_settings(settings)
                st.success("Maklumat sekolah dikemaskini!")
                st.rerun()

        with col_s2:
            st.write("### 👤 Pengurusan Pegawai Pentadbiran")
            jawatan_list = [
                "Guru Besar", "PK Pentadbiran", "PK HEM", "PK Kokurikulum", 
                "PK Pendidikan Khas", "Pembantu Tadbir Asrama"
            ]
            
            sel_jawatan = st.selectbox("Pilih Jawatan untuk Diedit:", jawatan_list)
            
            with st.form(f"form_{sel_jawatan}"):
                curr = settings["staff"].get(sel_jawatan, {"nama": "", "gred": ""})
                n_nama = st.text_input("Nama Pegawai", value=curr["nama"])
                n_gred = st.text_input("Gred (cth: DG44)", value=curr["gred"])
                if st.form_submit_button("Simpan Pegawai"):
                    settings["staff"][sel_jawatan] = {"nama": n_nama, "gred": n_gred}
                    save_settings(settings)
                    st.success(f"Rekod {sel_jawatan} dikemaskini!")

        st.divider()
        col_st1, col_st2 = st.columns(2)
        
        with col_st1:
            st.write("### 🏠 Warden Asrama (Maksimum 3)")
            for i in range(1, 4):
                key = f"Warden {i}"
                curr = settings["staff"].get(key, {"nama": "", "gred": ""})
                with st.expander(f"Warden {i}: {curr['nama']}"):
                    w_nama = st.text_input(f"Nama Warden {i}", value=curr["nama"], key=f"wn_{i}")
                    w_gred = st.text_input(f"Gred Warden {i}", value=curr["gred"], key=f"wg_{i}")
                    if st.button(f"Simpan Warden {i}"):
                        settings["staff"][key] = {"nama": w_nama, "gred": w_gred}
                        save_settings(settings)
                        st.rerun()

        with col_st2:
            st.write("### 🧑‍🤝‍🧑 PPM Asrama (Maksimum 2)")
            for i in range(1, 3):
                key = f"PPM Asrama {i}"
                curr = settings["staff"].get(key, {"nama": "", "gred": ""})
                with st.expander(f"PPM {i}: {curr['nama']}"):
                    p_nama = st.text_input(f"Nama PPM {i}", value=curr["nama"], key=f"pn_{i}")
                    p_gred = st.text_input(f"Gred PPM {i}", value=curr["gred"], key=f"pg_{i}")
                    if st.button(f"Simpan PPM {i}"):
                        settings["staff"][key] = {"nama": p_nama, "gred": p_gred}
                        save_settings(settings)
                        st.rerun()

    # --- TAB LAIN (Kekalkan fungsi sedia ada dari v8.0) ---
    with tabs[1]:
        st.subheader("🏠 Maklumat Pelajar Asrama")
        if not data_asrama.empty:
            st.dataframe(data_asrama, use_container_width=True)
            sel_p = st.selectbox("Pilih Pelajar untuk Surat PDF:", data_asrama.index, format_func=lambda x: str(data_asrama.loc[x, data_asrama.columns[0]]))
            if st.button("Jana Surat Tawaran PDF"):
                pdf_bytes = generate_offer_letter(data_asrama.loc[sel_p])
                st.download_button("Muat Turun Surat", pdf_bytes, f"Surat_{data_asrama.loc[sel_p].iloc[0]}.pdf", "application/pdf")
        else: st.info("Tiada data.")

    # (Nota: Tab Pendaftaran, Kehadiran, dan Inventori kekal seperti kod v8.0 sebelumnya)