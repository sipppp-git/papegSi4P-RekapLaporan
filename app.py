import streamlit as st
import tesRekap123  # Mengimpor script otomatisasi Anda

st.set_page_config(page_title="Update Rekap LCS", page_icon="🔄")

st.title("Sistem Otomatisasi Rekap LCS")
st.write("Tekan tombol di bawah untuk memerintahkan bot melakukan rekap data terbaru.")

if st.button("🔄 Update Data Rekap LCS", type="primary"):
    with st.spinner("Bot sedang bekerja... Mohon tunggu, proses ini memakan waktu beberapa menit."):
        try:
            # Memanggil fungsi utama dari script Anda
            hasil = tesRekap123.jalankan_bot()
            st.success(f"Berhasil! {hasil}")
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")