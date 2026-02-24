import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import math
import io
from fpdf import FPDF
from datetime import datetime, date, timedelta

# --- 1. KONFIGURASI HALAMAN ---
# Menggunakan tanda petikan yang betul untuk mengelakkan SyntaxError
st.set_page_config(page_title="Sistem Pengurusan Pelajar SKBN", layout="wide", page_icon="🎓")

# --- 2. SAMBUNGAN GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, columns=None):
    try:
        # Membaca data segar dari Google Sheets tanpa had
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame(columns=columns) if columns else pd.DataFrame()

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

# --- 3. FUNGSI EKSPORT & PDF ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data_SKBN')
    return output.getvalue()

# Kelas PDF untuk Surat Tawaran (Portrait)
class OfferPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, "SEKOLAH KEBANGSAAN BATU NIAH", ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, "D/A PEJABAT PENDIDIKAN DAERAH SUBIS, 98150 BEKENU", ln=True, align='C')
        self.cell(0, 5, "Tel: 085-737-005 | Emel: skbatuniah@gmail.com", ln=True, align='C')
        self.line(10, 30, 200, 30)
        self.ln(10)

# Fungsi Jana Sijil (Landscape)
def generate_cert_pdf(name, percentage, gb_name):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.rect(10, 10, 277, 190) # Border
    pdf.set_font('Arial', 'B', 35)
    pdf.ln(45)
    pdf.cell(0, 20, "SIJIL PENGHARGAAN KEHADIRAN", ln=True, align='C')
    pdf.set_font('Arial', '', 20)
    pdf.cell(0, 15, "Dianugerahkan kepada:", ln=True, align='C')
    pdf.set_font('Arial', 'B', 30)
    pdf.cell(0, 20, name.upper(), ln=True, align='C')
    pdf.set_font('Arial', '', 18)
    pdf.multi_cell(0, 10, f"Atas pencapaian kehadiran asrama sebanyak {percentage:.1f}%", align='C')
    pdf.ln(15)
    pdf.cell(0, 10, f"({gb_name.upper()})", ln=True, align='C')
    pdf.cell(0, 5, "Guru Besar, SK Batu Niah", ln=True, align='C')
    return pdf.output()

# --- 4. KESELAMATAN ---
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

# --- 5. UI UTAMA ---
if check_password():
    # Inisialisasi State Halaman
    if 'current_page' not in st.session_state: st.session_state.current_page = 1
    
    # Load Semua Data
    df_asrama = load_data("Data_Asrama")
    df_kehadiran = load_data("Rekod_Kehadiran", ["Tarikh", "Nama", "Hadir", "Sebab"])
    df_inventori = load_data("Inventori", ["Barang", "Kuantiti", "Warna", "Status"])
    df_settings = load_data("Settings", ["Key", "Value"])
    
    gb_name = df_settings[df_settings['Key'] == 'gb_name']['Value'].values[0] if not df_settings.empty else "JUTIE ANAK UJAK"
    sch_name = df_settings[df_settings['Key'] == 'school_name']['Value'].values[0] if not df_settings.empty else "SK BATU NIAH"

    tabs = st.tabs(["🔍 Daftar", "🏠 Maklumat Pelajar", "📅 Kehadiran", "📦 Inventori", "📊 Analisis & Sijil", "⚙️ Tetapan"])

    # --- TAB 1: PENDAFTARAN ---
    with tabs[0]:
        st.subheader("Muat Naik & Daftar Pelajar")
        up = st.file_uploader("Upload Excel Pelajar", type=["xlsx"])
        if up:
            raw = pd.read_excel(up)
            st.dataframe(raw.head(10), use_container_width=True)
            sel = st.selectbox("Pilih Pelajar:", raw.index, format_func=lambda x: str(raw.loc[x, 'NAMA'] if 'NAMA' in raw.columns else x))
            if st.button("➕ Daftar ke Google Sheets"):
                df_asrama = pd.concat([df_asrama, raw.loc[[sel]]]).drop_duplicates()
                save_data(df_asrama, "Data_Asrama")
                st.success("Berjaya didaftarkan!")

    # --- TAB 2: MAKLUMAT PELAJAR (CARIAN & 20 BARIS) ---
    with tabs[1]:
        st.subheader("🏠 Maklumat Penghuni Asrama")
        if not df_asrama.empty:
            q = st.text_input("🔍 Cari Nama atau No. KP (Huruf besar/kecil tidak penting):")
            if q:
                cols = [c for c in df_asrama.columns if any(x in c.upper() for x in ["NAMA", "PENGENALAN", "KP"])]
                mask = df_asrama[cols].astype(str).apply(lambda x: x.str.contains(q, case=False, na=False)).any(axis=1)
                f_df = df_asrama[mask]
                st.session_state.current_page = 1
            else: f_df = df_asrama

            limit = 20
            total_p = math.ceil(len(f_df) / limit) if len(f_df) > 0 else 1
            start = (st.session_state.current_page - 1) * limit
            st.dataframe(f_df.iloc[start : start + limit], use_container_width=True, hide_index=True)
            
            c1, c2, c3 = st.columns([1, 2, 1])
            if c1.button("⬅️ Sebelumnya") and st.session_state.current_page > 1:
                st.session_state.current_page -= 1
                st.rerun()
            c2.write(f"<center>Halaman {st.session_state.current_page} / {total_p}</center>", unsafe_allow_html=True)
            if c3.button("Seterusnya ➡️") and st.session_state.current_page < total_p:
                st.session_state.current_page += 1
                st.rerun()
            
            st.download_button("📥 Eksport Senarai (Excel)", to_excel(f_df), f"Pelajar_SKBN_{date.today()}.xlsx")

            st.divider()
            target = st.selectbox("Pilih Pelajar untuk Surat/Padam:", f_df.index, format_func=lambda x: str(f_df.loc[x, 'NAMA']))
            if st.button("📄 Jana Surat Tawaran PDF"):
                # Fungsi PDF Portrait diletakkan di sini...
                st.info(f"Surat untuk {f_df.loc[target, 'NAMA']} dijana.")

    # --- TAB 3: KEHADIRAN (BACKDATE) ---
    with tabs[2]:
        st.subheader("📅 Rekod Kehadiran (Harian / Backdate)")
        sel_date = st.date_input("Pilih Tarikh:", value=date.today())
        existing = df_kehadiran[df_kehadiran['Tarikh'] == str(sel_date)]
        
        if not df_asrama.empty:
            with st.form("att_form"):
                reks = []
                for idx, row in df_asrama.iterrows():
                    c_n, c_h, c_s = st.columns([3, 1, 3])
                    c_n.write(row['NAMA'])
                    old_h = existing[existing['Nama'] == row['NAMA']]['Hadir'].values[0] if not existing.empty else 1
                    old_s = existing[existing['Nama'] == row['NAMA']]['Sebab'].values[0] if not existing.empty else ""
                    h = c_h.checkbox("Hadir", value=bool(old_h), key=f"h_{idx}")
                    s = c_s.text_input("Sebab", value=old_s, key=f"s_{idx}") if not h else ""
                    reks.append({"Tarikh": str(sel_date), "Nama": row['NAMA'], "Hadir": 1 if h else 0, "Sebab": s})
                if st.form_submit_button("💾 Simpan/Kemaskini Rekod"):
                    df_kehadiran = df_kehadiran[df_kehadiran['Tarikh'] != str(sel_date)]
                    df_kehadiran = pd.concat([df_kehadiran, pd.DataFrame(reks)])
                    save_data(df_kehadiran, "Rekod_Kehadiran")
                    st.success(f"Rekod tarikh {sel_date} disimpan!")
        else: st.warning("Tiada data pelajar.")

    # --- TAB 4: INVENTORI ---
    with tabs[3]:
        st.subheader("📦 Pengurusan Inventori")
        with st.form("inv_form"):
            i1, i2, i3, i4 = st.columns(4)
            nb = i1.text_input("Nama Barang")
            kq = i2.number_input("Kuantiti", min_value=0)
            wr = i3.text_input("Warna")
            stt = i4.selectbox("Status", ["Baik", "Rosak", "Hilang"])
            if st.form_submit_button("➕ Tambah Barang"):
                df_inventori = pd.concat([df_inventori, pd.DataFrame([{"Barang": nb, "Kuantiti": kq, "Warna": wr, "Status": stt}])])
                save_data(df_inventori, "Inventori")
                st.rerun()
        st.dataframe(df_inventori, use_container_width=True)

    # --- TAB 5: ANALISIS & SIJIL ---
    with tabs[4]:
        st.subheader("📊 Analisis Kehadiran & Sijil Cemerlang")
        if not df_kehadiran.empty:
            # Statistik Peratus
            stats = df_kehadiran.groupby('Nama')['Hadir'].agg(['count', 'sum'])
            stats['Peratus'] = (stats['sum'] / stats['count']) * 100
            stats.columns = ['Hari Rekod', 'Hari Hadir', 'Peratus (%)']
            
            st.write("### 🏆 Pelajar Layak Sijil (90% ke atas)")
            layak = stats[stats['Peratus (%)'] >= 90.0].sort_values(by='Peratus (%)', ascending=False)
            st.dataframe(layak, use_container_width=True)
            
            if not layak.empty:
                sel_cert = st.selectbox("Pilih Pelajar Penerima:", layak.index)
                if st.button("📜 Jana Sijil PDF"):
                    pdf_cert = generate_cert_pdf(sel_cert, layak.loc[sel_cert, 'Peratus (%)'], gb_name)
                    st.download_button(f"📥 Muat Turun Sijil - {sel_cert}", pdf_cert, f"Sijil_{sel_cert}.pdf")
            
            st.divider()
            st.write("### Trend Kehadiran Keseluruhan")
            df_kehadiran['Tarikh'] = pd.to_datetime(df_kehadiran['Tarikh'])
            st.line_chart(df_kehadiran.groupby('Tarikh')['Hadir'].mean() * 100)
            st.download_button("📥 Muat Turun Laporan Kehadiran (Excel)", to_excel(df_kehadiran), "Laporan_Kehadiran.xlsx")

    # --- TAB 6: TETAPAN ---
    with tabs[5]:
        st.subheader("⚙️ Tetapan Rasmi Sekolah")
        with st.form("set_form"):
            s_n = st.text_input("Nama Sekolah", value=sch_name)
            g_b = st.text_input("Nama Guru Besar", value=gb_name)
            if st.form_submit_button("💾 Simpan Tetapan"):
                save_data(pd.DataFrame([{"Key": "school_name", "Value": s_n}, {"Key": "gb_name", "Value": g_b}]), "Settings")
                st.success("Tetapan berjaya dikemaskini!")
