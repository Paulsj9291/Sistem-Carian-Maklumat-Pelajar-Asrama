import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import math
import io
from fpdf import FPDF
from datetime import datetime, date

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Pengurusan Pelajar SKBN", layout="wide", page_icon="🎓")

# --- 2. SAMBUNGAN GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, columns=None):
    try:
        # Membaca data tanpa had baris untuk kelancaran sistem
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame(columns=columns) if columns else pd.DataFrame()

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

# --- 3. KESELAMATAN (LOG MASUK) ---
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

# --- 4. PENJANA PDF RASMI SKBN ---
class PDF(FPDF):
    def header(self):
        # Mengambil info sekolah dari Settings sheet
        settings_df = load_data("Settings")
        sch_name = settings_df[settings_df['Key'] == 'school_name']['Value'].values[0] if not settings_df.empty else "SK BATU NIAH"
        
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, sch_name, ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, "D/A PEJABAT PENDIDIKAN DAERAH SUBIS, 98150 BEKENU", ln=True, align='C')
        self.cell(0, 5, "Tel: 085-737-005 | Emel: skbatuniah@gmail.com", ln=True, align='C')
        self.line(10, 30, 200, 30)
        self.ln(10)

def generate_pdf(row, settings_df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 11)
    
    # Rujukan & Tarikh
    pdf.cell(0, 10, f"Ruj. Kami: SKBN.T.700-10/2/1 ({row.name})", ln=True, align='R')
    pdf.cell(0, 5, f"Tarikh: {datetime.now().strftime('%d %B %Y')}", ln=True, align='R')
    pdf.ln(5)
    
    # Penerima
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, str(row.get('NAMA', 'PELAJAR')).upper(), ln=True)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 5, "Niah, Sarawak.", ln=True)
    pdf.ln(10)
    
    # Tajuk
    pdf.set_font('Arial', 'B', 11)
    pdf.multi_cell(0, 5, "TAWARAN MASUK KE ASRAMA SK BATU NIAH BAGI SESI TAHUN 2025-2026")
    pdf.ln(5)
    
    # Kandungan
    pdf.set_font('Arial', '', 11)
    msg = f"Sukacita dimaklumkan bahawa anak jagaan tuan, {row.get('NAMA', 'Pelajar')} telah ditawarkan menduduki asrama bagi sesi 2025-2026."
    pdf.multi_cell(0, 6, msg)
    pdf.ln(15)
    
    # Tandatangan Guru Besar
    gb = settings_df[settings_df['Key'] == 'gb_name']['Value'].values[0] if not settings_df.empty else "JUTIE ANAK UJAK"
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, f"({gb.upper()})", ln=True)
    pdf.cell(0, 5, "Guru Besar, SK Batu Niah", ln=True)
    
    return pdf.output()

# --- 5. UI UTAMA ---
if check_password():
    # Inisialisasi Session State untuk Halaman
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    # Muat Data Semua Tab
    df_asrama = load_data("Data_Asrama")
    df_kehadiran = load_data("Rekod_Kehadiran", ["Tarikh", "Nama", "Hadir", "Sebab"])
    df_inventori = load_data("Inventori", ["Barang", "Kuantiti", "Warna", "Status"])
    df_settings = load_data("Settings", ["Key", "Value"])

    # Sidebar
    with st.sidebar:
        st.title("🏫 Menu Utama")
        st.info(f"Sekolah: {df_settings[df_settings['Key'] == 'school_name']['Value'].values[0] if not df_settings.empty else 'SK Batu Niah'}")
        if st.button("🚪 Log Keluar"):
            st.session_state.clear()
            st.rerun()

    tabs = st.tabs(["🔍 Pendaftaran", "🏠 Maklumat Asrama", "📅 Kehadiran", "📦 Inventori", "⚙️ Tetapan"])

    # --- TAB 1: PENDAFTARAN ---
    with tabs[0]:
        st.subheader("Muat Naik Data Pelajar (Excel)")
        up_file = st.file_uploader("Pilih Fail Excel", type=["xlsx"])
        if up_file:
            raw = pd.read_excel(up_file)
            st.dataframe(raw.head(10), use_container_width=True)
            sel = st.selectbox("Pilih Pelajar untuk Didaftar:", raw.index, format_func=lambda x: str(raw.loc[x, 'NAMA'] if 'NAMA' in raw.columns else x))
            if st.button("➕ Daftar ke Asrama"):
                new_row = raw.loc[[sel]]
                df_asrama = pd.concat([df_asrama, new_row]).drop_duplicates()
                save_data(df_asrama, "Data_Asrama")
                st.success("Berjaya disimpan ke Google Sheets!")

    # --- TAB 2: MAKLUMAT ASRAMA (CARIAN & HALAMAN 20 BARIS) ---
    with tabs[1]:
        st.subheader("🏠 Maklumat Pelajar Asrama")
        if not df_asrama.empty:
            # Sistem Carian Pintar (Nama/IC - Case Insensitive)
            q = st.text_input("🔍 Cari Nama atau No. Pengenalan (Contoh: rachel):")
            
            if q:
                # Menghadkan carian pada lajur berkaitan sahaja
                cols = [c for c in df_asrama.columns if any(x in c.upper() for x in ["NAMA", "PENGENALAN", "KP"])]
                mask = df_asrama[cols].astype(str).apply(lambda x: x.str.contains(q, case=False, na=False)).any(axis=1)
                f_df = df_asrama[mask]
                st.session_state.current_page = 1
            else:
                f_df = df_asrama

            # Sistem Halaman (Pagination) 20 Baris
            limit = 20
            total_p = math.ceil(len(f_df) / limit) if len(f_df) > 0 else 1
            
            start = (st.session_state.current_page - 1) * limit
            st.dataframe(f_df.iloc[start : start + limit], use_container_width=True, hide_index=True)
            
            # Navigasi Halaman
            c1, c2, c3 = st.columns([1, 2, 1])
            if c1.button("⬅️ Sebelumnya") and st.session_state.current_page > 1:
                st.session_state.current_page -= 1
                st.rerun()
            c2.write(f"<center>Halaman {st.session_state.current_page} / {total_p}</center>", unsafe_allow_html=True)
            if c3.button("Seterusnya ➡️") and st.session_state.current_page < total_p:
                st.session_state.current_page += 1
                st.rerun()

            # Fungsi Tindakan (PDF & Padam)
            st.divider()
            target = st.selectbox("Pilih Pelajar untuk Tindakan:", f_df.index, format_func=lambda x: str(f_df.loc[x, 'NAMA']))
            b_c1, b_c2 = st.columns(2)
            if b_c1.button("📄 Jana PDF Tawaran"):
                pdf_b = generate_pdf(f_df.loc[target], df_settings)
                st.download_button("📥 Muat Turun Surat", pdf_b, f"Surat_{f_df.loc[target, 'NAMA']}.pdf")
            if b_c2.button("🗑️ Padam Rekod"):
                df_asrama = df_asrama.drop(target)
                save_data(df_asrama, "Data_Asrama")
                st.rerun()
        else:
            st.info("Tiada data pelajar asrama.")

    # --- TAB 3: KEHADIRAN ---
    with tabs[2]:
        st.subheader("📅 Rekod Kehadiran")
        t_date = st.date_input("Tarikh", value=date.today())
        if t_date.weekday() >= 5:
            st.warning("Hari ini Hujung Minggu (Sabtu/Ahad).")
        
        if not df_asrama.empty:
            with st.form("form_att"):
                reks = []
                for idx, row in df_asrama.iterrows():
                    col_n, col_h, col_s = st.columns([3, 1, 3])
                    h = col_h.checkbox("Hadir", value=True, key=f"h_{idx}")
                    s = col_s.text_input("Sebab", key=f"s_{idx}") if not h else ""
                    reks.append({"Tarikh": str(t_date), "Nama": row['NAMA'], "Hadir": 1 if h else 0, "Sebab": s})
                if st.form_submit_button("💾 Simpan Kehadiran"):
                    new_att = pd.DataFrame(reks)
                    df_kehadiran = pd.concat([df_kehadiran, new_att])
                    save_data(df_kehadiran, "Rekod_Kehadiran")
                    st.success("Data kehadiran disimpan ke Google Sheets!")

    # --- TAB 4: INVENTORI ---
    with tabs[3]:
        st.subheader("📦 Inventori Asrama")
        with st.form("form_inv"):
            i1, i2, i3, i4 = st.columns(4)
            nb = i1.text_input("Barang")
            kq = i2.number_input("Kuantiti", min_value=0)
            wr = i3.text_input("Warna")
            stt = i4.selectbox("Status", ["Baik", "Rosak", "Hilang"])
            if st.form_submit_button("➕ Tambah Barang"):
                df_inventori = pd.concat([df_inventori, pd.DataFrame([{"Barang": nb, "Kuantiti": kq, "Warna": wr, "Status": stt}])])
                save_data(df_inventori, "Inventori")
                st.rerun()
        st.dataframe(df_inventori, use_container_width=True)

    # --- TAB 5: TETAPAN ---
    with tabs[4]:
        st.subheader("⚙️ Tetapan Sekolah & Pegawai")
        with st.form("form_set"):
            s_n = st.text_input("Nama Sekolah", value=df_settings[df_settings['Key'] == 'school_name']['Value'].values[0] if not df_settings.empty else "SK BATU NIAH")
            g_b = st.text_input("Nama Guru Besar", value=df_settings[df_settings['Key'] == 'gb_name']['Value'].values[0] if not df_settings.empty else "JUTIE ANAK UJAK")
            if st.form_submit_button("💾 Simpan Tetapan"):
                save_data(pd.DataFrame([{"Key": "school_name", "Value": s_n}, {"Key": "gb_name", "Value": g_b}]), "Settings")
                st.success("Tetapan dikemaskini!")
