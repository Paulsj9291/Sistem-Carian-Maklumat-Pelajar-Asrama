import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import math
import io
import os
from fpdf import FPDF
from datetime import datetime, date

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem SKBN Online Pro", layout="wide", page_icon="🎓")

# --- 2. SAMBUNGAN GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, columns=None):
    try:
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame(columns=columns) if columns else pd.DataFrame()

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

# --- 3. KESELAMATAN ---
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

# --- 4. PENJANA PDF (FORMAT SKBN) ---
class PDF(FPDF):
    def header(self):
        # Mengambil logo dan nama dari settings
        settings = load_data("Settings", ["Key", "Value"])
        school_name = settings[settings['Key'] == 'school_name']['Value'].values[0] if not settings.empty else "SK BATU NIAH"
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, school_name, ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, "D/A PEJABAT PENDIDIKAN DAERAH SUBIS, 98150 BEKENU", ln=True, align='C')
        self.line(10, 28, 200, 28)
        self.ln(10)

def generate_offer_letter(row, settings):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 10, f"Ruj. Kami: SKBN.T.700-10/2/1 ({row.name})", ln=True, align='R')
    pdf.cell(0, 5, f"Tarikh: {datetime.now().strftime('%d %B %Y')}", ln=True, align='R')
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, str(row.get('Nama', 'PELAJAR')).upper(), ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, "Rumah Kediaman Pelajar, Niah, Sarawak.", ln=True)
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 11)
    pdf.multi_cell(0, 5, "TAWARAN MASUK KE ASRAMA SK BATU NIAH BAGI SESI TAHUN 2025-2026")
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    nama = row.get('Nama', 'Pelajar')
    kelas = row.get('Kelas', 'N/A')
    pdf.multi_cell(0, 6, f"Sukacita dimaklumkan bahawa anak jagaan tuan, {nama} dari kelas {kelas} telah ditawarkan menduduki asrama SK Batu Niah bagi sesi 2025-2026.")
    pdf.ln(10)
    # Ambil nama Guru Besar dari Settings
    gb_name = settings[settings['Key'] == 'gb_name']['Value'].values[0] if 'gb_name' in settings['Key'].values else "JUTIE ANAK UJAK"
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, f"({gb_name.upper()})", ln=True)
    pdf.cell(0, 5, "Guru Besar, SK Batu Niah", ln=True)
    return pdf.output()

# --- 5. UI UTAMA ---
if check_password():
    # Load Data dari Google Sheets
    df_asrama = load_data("Data_Asrama", ["Nama", "Kelas", "No. KP", "Bangsa", "Agama"])
    df_kehadiran = load_data("Rekod_Kehadiran", ["Tarikh", "Nama", "Hadir", "Sebab"])
    df_inventori = load_data("Inventori", ["Barang", "Kuantiti", "Warna", "Status"])
    df_settings = load_data("Settings", ["Key", "Value"])

    # Sidebar
    with st.sidebar:
        st.title("🏫 SK Batu Niah")
        if st.button("🚪 Log Keluar"):
            st.session_state.clear()
            st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Daftar", "🏠 Maklumat Asrama", "📅 Kehadiran", "📦 Inventori", "⚙️ Tetapan"])

    # --- TAB 1: PENDAFTARAN ---
    with tab1:
        st.subheader("Pendaftaran Pelajar Baru")
        file = st.file_uploader("Upload Excel Pelajar", type=["xlsx"])
        if file:
            raw_df = pd.read_excel(file)
            st.dataframe(raw_df.head(10))
            sel_idx = st.selectbox("Pilih Pelajar untuk Didaftar:", raw_df.index, format_func=lambda x: str(raw_df.loc[x, raw_df.columns[0]]))
            if st.button("➕ Daftar ke Google Sheets"):
                new_row = raw_df.loc[[sel_idx]]
                df_asrama = pd.concat([df_asrama, new_row]).drop_duplicates()
                save_data(df_asrama, "Data_Asrama")
                st.success("Berjaya disimpan ke Google Sheets!")

    # --- TAB 2: MAKLUMAT ASRAMA (DENGAN CARIAN PINTAR & HALAMAN) ---
    with tab2:
        st.subheader("🏠 Pengurusan Maklumat Pelajar Asrama")
        
        if not df_asrama.empty:
            # A. Sistem Carian Pintar (Nama & No. KP Sahaja)
            search_cols = [c for c in df_asrama.columns if "NAMA" in c.upper() or "PENGENALAN" in c.upper() or "NO. KP" in c.upper()]
            query = st.text_input("Cari Nama atau No. Pengenalan (Huruf besar/kecil tidak penting):")
            
            if query:
                mask = df_asrama[search_cols].astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
                results = df_asrama[mask]
            else:
                results = df_asrama

            # B. Sistem Halaman (20 Baris)
            rows_per_page = 20
            total_pages = math.ceil(len(results) / rows_per_page) if len(results) > 0 else 1
            
            if 'p2_page' not in st.session_state: st.session_state.p2_page = 1
            
            start_idx = (st.session_state.p2_page - 1) * rows_per_page
            st.dataframe(results.iloc[start_idx : start_idx + rows_per_page], use_container_width=True, hide_index=True)
            
            # Navigasi Butang
            c_p1, c_p2, c_p3 = st.columns([1, 2, 1])
            if c_p1.button("⬅️ Sebelumnya", key="prev_asr") and st.session_state.p2_page > 1:
                st.session_state.p2_page -= 1
                st.rerun()
            c_p2.write(f"<center>Halaman {st.session_state.p2_page} / {total_pages}</center>", unsafe_allow_html=True)
            if c_p3.button("Seterusnya ➡️", key="next_asr") and st.session_state.p2_page < total_pages:
                st.session_state.p2_page += 1
                st.rerun()

            # C. Jana PDF & Edit
            st.divider()
            target_p = st.selectbox("Pilih Pelajar untuk Surat/Edit:", results.index, format_func=lambda x: str(results.loc[x, 'Nama']))
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("📄 Jana Surat Tawaran PDF"):
                pdf_bytes = generate_offer_letter(results.loc[target_p], df_settings)
                st.download_button("📥 Muat Turun PDF", pdf_bytes, f"Surat_{results.loc[target_p, 'Nama']}.pdf", "application/pdf")
            
            if col_b2.button("🗑️ Padam Pelajar"):
                df_asrama = df_asrama.drop(target_p)
                save_data(df_asrama, "Data_Asrama")
                st.warning("Rekod telah dipadam dari Google Sheets.")
                st.rerun()
        else:
            st.info("Tiada data asrama. Sila daftar di Tab 1.")

    # --- TAB 3: KEHADIRAN ---
    with tab3:
        st.subheader("📅 Rekod Kehadiran Harian")
        sel_date = st.date_input("Pilih Tarikh", value=date.today())
        is_weekend = sel_date.weekday() >= 5
        
        if is_weekend and not st.checkbox("Tanda manual untuk hari cuti/hujung minggu"):
            st.warning("Hari ini adalah hujung minggu. Rekod dikecualikan.")
        else:
            if not df_asrama.empty:
                with st.form("att_form"):
                    att_records = []
                    for i, r in df_asrama.iterrows():
                        c_n, c_h, c_s = st.columns([3, 1, 3])
                        h = c_h.checkbox("Hadir", value=True, key=f"att_{i}")
                        s = c_s.text_input("Sebab (Jika tidak hadir)", key=f"seb_{i}") if not h else ""
                        att_records.append({"Tarikh": str(sel_date), "Nama": r['Nama'], "Hadir": 1 if h else 0, "Sebab": s})
                    
                    if st.form_submit_button("💾 Simpan Kehadiran ke Google Sheets"):
                        new_att = pd.DataFrame(att_records)
                        # Padam data tarikh sama jika ada (update)
                        df_kehadiran = df_kehadiran[df_kehadiran['Tarikh'] != str(sel_date)] if not df_kehadiran.empty else df_kehadiran
                        df_kehadiran = pd.concat([df_kehadiran, new_att])
                        save_data(df_kehadiran, "Rekod_Kehadiran")
                        st.success("Kehadiran berjaya dihantar!")

    # --- TAB 4: INVENTORI ---
    with tab4:
        st.subheader("📦 Inventori Barang Asrama")
        with st.form("inv_form"):
            col_i1, col_i2, col_i3, col_i4 = st.columns(4)
            b = col_i1.text_input("Nama Barang")
            q = col_i2.number_input("Kuantiti", min_value=0)
            w = col_i3.text_input("Warna")
            s = col_i4.selectbox("Status", ["Baik", "Rosak", "Hilang"])
            if st.form_submit_button("➕ Tambah/Update Barang"):
                new_inv = pd.DataFrame([{"Barang": b, "Kuantiti": q, "Warna": w, "Status": s}])
                df_inventori = pd.concat([df_inventori, new_inv])
                save_data(df_inventori, "Inventori")
                st.rerun()
        st.dataframe(df_inventori, use_container_width=True)

    # --- TAB 5: TETAPAN ---
    with tab5:
        st.subheader("⚙️ Tetapan Sekolah & Pegawai")
        with st.form("set_form"):
            curr_name = df_settings[df_settings['Key'] == 'school_name']['Value'].values[0] if 'school_name' in df_settings['Key'].values else "SK BATU NIAH"
            curr_gb = df_settings[df_settings['Key'] == 'gb_name']['Value'].values[0] if 'gb_name' in df_settings['Key'].values else "JUTIE ANAK UJAK"
            
            new_s_name = st.text_input("Nama Sekolah", value=curr_name)
            new_gb_name = st.text_input("Nama Guru Besar", value=curr_gb)
            
            if st.form_submit_button("💾 Simpan Tetapan ke Google Sheets"):
                set_df = pd.DataFrame([
                    {"Key": "school_name", "Value": new_s_name},
                    {"Key": "gb_name", "Value": new_gb_name}
                ])
                save_data(set_df, "Settings")
                st.success("Tetapan dikemaskini!")
