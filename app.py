import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import math
import io
from fpdf import FPDF
from datetime import datetime, date, timedelta

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Pengurusan Pelajar SKBN", layout="wide", page_icon="🎓")

# --- 2. SAMBUNGAN GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        # ttl=0 memastikan data sentiasa segar dari Google Sheets
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)
    st.cache_data.clear()

# --- 3. FUNGSI EKSPORT & PDF ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data_SKBN')
    return output.getvalue()

class PDF_Standard(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, "SEKOLAH KEBANGSAAN BATU NIAH", ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, "D/A PEJABAT PENDIDIKAN DAERAH SUBIS, 98150 BEKENU", ln=True, align='C')
        self.cell(0, 5, "Tel: 085-737-005 | Emel: skbatuniah@gmail.com", ln=True, align='C')
        self.line(10, 30, 200, 30)
        self.ln(10)

def generate_certificate(name, percentage, gb_name):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.rect(10, 10, 277, 190) # Border Sijil
    pdf.set_font('Arial', 'B', 35)
    pdf.ln(50)
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

# --- 4. KESELAMATAN (LOGIN) ---
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
    df_kehadiran = load_data("Rekod_Kehadiran")
    df_inventori = load_data("Inventori")
    df_settings = load_data("Settings")
    
    gb_name = df_settings[df_settings['Key'] == 'gb_name']['Value'].values[0] if not df_settings.empty else "JUTIE ANAK UJAK"
    sch_name = df_settings[df_settings['Key'] == 'school_name']['Value'].values[0] if not df_settings.empty else "SK BATU NIAH"

    tabs = st.tabs(["🔍 Daftar", "🏠 Maklumat Pelajar", "📅 Kehadiran", "📦 Inventori", "📊 Analisis & Sijil", "⚙️ Tetapan"])

    # --- TAB 1: PENDAFTARAN (FUNGSI PRATONTON DIBUANG UNTUK ELAK KELIRU) ---
    with tabs[0]:
        st.subheader("Muat Naik Data Pelajar Baru")
        up_file = st.file_uploader("Upload Excel Pelajar (.xlsx)", type=["xlsx"])
        if up_file:
            raw_data = pd.read_excel(up_file)
            st.info(f"Berjaya membaca {len(raw_data)} rekod dari fail Excel.")
            sel_idx = st.selectbox("Pilih Pelajar untuk Didaftar:", raw_data.index, 
                                   format_func=lambda x: str(raw_data.loc[x, 'NAMA'] if 'NAMA' in raw_data.columns else x))
            if st.button("➕ Daftar ke Google Sheets"):
                df_asrama = pd.concat([df_asrama, raw_data.loc[[sel_idx]]]).drop_duplicates()
                save_data(df_asrama, "Data_Asrama")
                st.success("Rekod pelajar telah berjaya didaftarkan!")

    # --- TAB 2: MAKLUMAT PELAJAR (CARIAN PINTAR & 20 BARIS) ---
    with tabs[1]:
        st.subheader("🏠 Maklumat Penghuni Asrama")
        if not df_asrama.empty:
            # KOTAK CARIAN LUAR (Case-Insensitive)
            q = st.text_input("🔍 CARI NAMA ATAU NO. KP (Huruf besar/kecil tidak penting):", 
                              placeholder="Contoh: rachel")

            # Logik Penapisan
            if q:
                search_cols = [c for c in df_asrama.columns if any(x in c.upper() for x in ["NAMA", "PENGENALAN", "KP"])]
                mask = df_asrama[search_cols].fillna('').astype(str).apply(
                    lambda x: x.str.contains(q, case=False, na=False)
                ).any(axis=1)
                f_df = df_asrama[mask]
                st.session_state.current_page = 1 # Reset ke page 1 jika carian berubah
            else:
                f_df = df_asrama

            # SISTEM HALAMAN (20 BARIS)
            limit = 20
            total_records = len(f_df)
            total_pages = math.ceil(total_records / limit) if total_records > 0 else 1
            start = (st.session_state.current_page - 1) * limit
            
            st.write(f"Menunjukkan {total_records} rekod ditemui.")
            st.dataframe(f_df.iloc[start : start + limit], use_container_width=True, hide_index=True)
            
            # Navigasi Butang
            if total_records > limit:
                c1, c2, c3 = st.columns([1, 2, 1])
                if c1.button("⬅️ Sebelumnya") and st.session_state.current_page > 1:
                    st.session_state.current_page -= 1
                    st.rerun()
                c2.write(f"<center>Halaman {st.session_state.current_page} / {total_pages}</center>", unsafe_allow_html=True)
                if c3.button("Seterusnya ➡️") and st.session_state.current_page < total_pages:
                    st.session_state.current_page += 1
                    st.rerun()
            
            st.download_button("📥 Eksport Senarai (Excel)", to_excel(f_df), f"Senarai_SKBN_{date.today()}.xlsx")
        else:
            st.info("Pangkalan data kosong.")

    # --- TAB 3: KEHADIRAN (BACKDATE & UPDATE) ---
    with tabs[2]:
        st.subheader("📅 Rekod Kehadiran (Harian / Backdate)")
        sel_date = st.date_input("Pilih Tarikh:", value=date.today())
        # Semak data sedia ada untuk tarikh dipilih
        existing = df_kehadiran[df_kehadiran['Tarikh'] == str(sel_date)] if not df_kehadiran.empty else pd.DataFrame()
        
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
                    # Buang rekod lama untuk tarikh ini dan ganti yang baru
                    df_kehadiran = df_kehadiran[df_kehadiran['Tarikh'] != str(sel_date)] if not df_kehadiran.empty else df_kehadiran
                    df_kehadiran = pd.concat([df_kehadiran, pd.DataFrame(reks)])
                    save_data(df_kehadiran, "Rekod_Kehadiran")
                    st.success(f"Rekod bagi {sel_date} berjaya disimpan!")

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

    # --- TAB 5: ANALISIS & SIJIL (90%+) ---
    with tabs[4]:
        st.subheader("📊 Analisis Kehadiran & Sijil Cemerlang")
        if not df_kehadiran.empty:
            df_kehadiran['Hadir'] = pd.to_numeric(df_kehadiran['Hadir'])
            stats = df_kehadiran.groupby('Nama')['Hadir'].agg(['count', 'sum'])
            stats['Peratus'] = (stats['sum'] / stats['count']) * 100
            stats.columns = ['Hari Rekod', 'Hari Hadir', 'Peratus (%)']
            
            st.write("### 🏆 Pelajar Layak Sijil (90% ke atas)")
            layak = stats[stats['Peratus (%)'] >= 90.0].sort_values(by='Peratus (%)', ascending=False)
            st.dataframe(layak, use_container_width=True)
            
            if not layak.empty:
                sel_cert = st.selectbox("Pilih Pelajar:", layak.index)
                if st.button("📜 Jana Sijil PDF"):
                    pdf_b = generate_certificate(sel_cert, layak.loc[sel_cert, 'Peratus (%)'], gb_name)
                    st.download_button(f"📥 Muat Turun Sijil", pdf_b, f"Sijil_{sel_cert}.pdf")
            
            st.divider()
            st.write("### Trend Kehadiran Mingguan/Bulanan")
            df_kehadiran['Tarikh'] = pd.to_datetime(df_kehadiran['Tarikh'])
            st.line_chart(df_kehadiran.groupby('Tarikh')['Hadir'].mean() * 100)
        else: st.warning("Data kehadiran tidak mencukupi.")

    # --- TAB 6: TETAPAN ---
    with tabs[5]:
        st.subheader("⚙️ Tetapan Rasmi Sekolah")
        with st.form("set_form"):
            s_n = st.text_input("Nama Sekolah", value=sch_name)
            g_b = st.text_input("Nama Guru Besar", value=gb_name)
            if st.form_submit_button("💾 Simpan Tetapan"):
                save_data(pd.DataFrame([{"Key": "school_name", "Value": s_n}, {"Key": "gb_name", "Value": g_b}]), "Settings")
                st.success("Tetapan dikemaskini!")
