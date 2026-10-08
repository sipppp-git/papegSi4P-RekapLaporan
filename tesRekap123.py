import os
import time
from datetime import datetime
import pytz # Tambahan untuk mengatur zona waktu Indonesia
import numpy as np
from PIL import Image, ImageOps
from keras.models import load_model
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import shutil


# ====================================================================
# 1. FUNGSI GOOGLE DRIVE API (KURIR PENGIRIM KE CLOUD)
# ====================================================================
def upload_ke_drive(nama_file_lokal):
    print("[-] Memulai proses unggah ke Google Drive...")
    kredensial = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        kredensial, scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    service = build('drive', 'v3', credentials=creds)
    folder_id = st.secrets["DRIVE_FOLDER_ID"]
    
    file_metadata = {'name': nama_file_lokal, 'parents': [folder_id]}
    media = MediaFileUpload(nama_file_lokal, mimetype='text/csv')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    
    # Hapus file lokal di server setelah sukses terkirim agar memori Streamlit tidak penuh
    if os.path.exists(nama_file_lokal):
        os.remove(nama_file_lokal)
        
    return file.get('id')

# ====================================================================
# 2. FUNGSI UTAMA (Dipanggil oleh Tombol di Streamlit)
# ====================================================================
def jalankan_bot():
    # Ambil akun dari brankas rahasia Streamlit
    username_anda = st.secrets["USERNAME_WEB"]
    password_anda = st.secrets["PASSWORD_WEB"]

    url_awal = "https://2025.epusluh.id/admin/login"

    # Set zona waktu paksa ke Waktu Indonesia Barat (Asia/Jakarta)
    tz_wib = pytz.timezone('Asia/Jakarta')
    waktu_sekarang = datetime.now(tz_wib)
    tgl_sekarang = waktu_sekarang.strftime("%Y-%m-%d")
    
    url_target = f"https://2025.epusluh.id/admin/content-lcs-reports?tableFilters[created_at][created_from]={tgl_sekarang}&tableFilters[created_at][created_to]={tgl_sekarang}&tableFilters[province_id][value]=37"

    print("[-] Memuat Model Pengawas CNN ke dalam memori...")
    model_ai = load_model("Model/keras_model.h5", compile=False)
    class_names = open("Model/labels.txt", "r").readlines()

    def fungsi_mata_ai(driver):
        nama_ss = "layar_live.png"
        driver.save_screenshot(nama_ss)
        
        image = Image.open(nama_ss).convert("RGB")
        size = (224, 224)
        image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
        
        image_array = np.asarray(image)
        normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
        
        data_input = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
        data_input[0] = normalized_image_array
        
        prediction = model_ai.predict(data_input, verbose=0)
        index = np.argmax(prediction)
        
        label_bersih = class_names[index].strip()
        if len(label_bersih) > 2:
            label_bersih = label_bersih.split(maxsplit=1)[-1]
            
        score = prediction[0][index]
        return label_bersih, score

    print(f"[-] Memulai otomasi rekap tanggal saat ini: {tgl_sekarang} (WIB)")
    
    # Pengaturan wajib agar browser bisa berjalan siluman di server Linux Streamlit
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080") # Paksa resolusi Full HD
    # PENYAMARAN EKSTRA: Mencegah layout web menciut di server Linux
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    # --- TAMBAHKAN 4 BARIS PENYAMARAN CLOUDFLARE DI SINI ---
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-web-security")

    driver = uc.Chrome(version_main=154, options=options)

    try:
        print(f"[-] Start Awal: Menuju halaman login -> {url_awal}")
        driver.get(url_awal)
        counter_blank = 0
        
        while True:
            time.sleep(5)
            status_layar, akurasi = fungsi_mata_ai(driver)
            print(f"[Model Pengawas] Mendeteksi Layar: '{status_layar}' (Keyakinan: {akurasi*100:.2f}%)")
            
            if status_layar == "LoginScreen":
                print("🤖 [Aksi Model] Mengisi form login...")
                user_input = driver.find_element(By.XPATH, "//input[@type='text' or @type='email' or @autocomplete='username' or contains(@placeholder, 'Username')]")
                pass_input = driver.find_element(By.XPATH, "//input[@type='password']")
                
                user_input.clear()
                user_input.send_keys(username_anda)
                pass_input.clear()
                pass_input.send_keys(password_anda)
                
                time.sleep(1)
                driver.find_element(By.XPATH, "//button[contains(., 'Masuk') or @type='submit']").click()
                time.sleep(5)
                continue
                
            elif status_layar in ["LoadingScreen", "WelcomeScreen"]:
                time.sleep(5)
                continue
                
            elif status_layar == "DashboardScreen":
                print(f"🤖 [Aksi Model] Dasbor terdeteksi! Mengalihkan ke link target...")
                
                # Fitur Debugging Gambar (Bisa dihapus nanti jika sudah lancar 100%)
                driver.save_screenshot("debug_layar.png")
                st.image("debug_layar.png", caption="Tangkapan Layar AI Terkini", use_column_width=True)
                
                driver.get(url_target)
                time.sleep(8)
                continue
                
            elif status_layar in ["BlankScreen", "404Screen"]:
                counter_blank += 1
                driver.refresh()
                time.sleep(10)
                if counter_blank > 3:
                    return "Gagal: Halaman terus-menerus Blank setelah 3 kali refresh."
                continue
                
            elif status_layar == "RekapScreen":
                print("🤖 [Aksi Model] Halaman rekapan valid! Mengekstrak data tabel...")
                
                js_script = """
                let rows = document.querySelectorAll('.fi-ta-row, table tr');
                
                // [REVISI] Kembalikan KOSONG agar dieksekusi oleh Python
                if (rows.length === 0) { return "KOSONG"; }
                
                let csv = [];
                let headers = [];
                let headerCols = document.querySelectorAll('.fi-ta-header-cell, table th');
                
                if (headerCols.length > 0) {
                    headerCols.forEach(col => headers.push('"' + col.innerText.trim().replace(/"/g,'""') + '"'));
                    csv.push(headers.join(","));
                }
                
                rows.forEach(row => {
                    let rowData = [];
                    let cols = row.querySelectorAll('.fi-ta-cell, td');
                    if (cols.length > 0) {
                        cols.forEach(col => {
                            let text = col.innerText.replace(/(\\r\\n|\\n|\\r)/gm," ").replace(/"/g,'""').trim();
                            rowData.push('"' + text + '"');
                        });
                        csv.push(rowData.join(","));
                    }
                });
                
                return "\\uFEFF" + csv.join("\\n");
                """
                
                hasil_csv = driver.execute_script(js_script)
                
                # 1. CABANG KOSONG: Tabel ada tapi tidak berisi data
                if hasil_csv == "KOSONG":
                    print("[-] Tabel kosong. Menggunakan template 'Belum_ada_laporan.csv'...")
                    jam_format = waktu_sekarang.strftime('%H.%M.%S')
                    nama_file_baru = f"Rekap Laporan LCS {waktu_sekarang.strftime('%d-%m-%Y')}{jam_format} (KOSONG).csv"
                    
                    # Duplikat file template ke nama baru
                    shutil.copy("Belum_ada_laporan.csv", nama_file_baru)
                    
                    # Lempar ke Drive
                    file_id = upload_ke_drive(nama_file_baru)
                    pesan_kosong = "Selesai: Data hari ini kosong. File CSV pereset telah diunggah."
                    print(f"[-] {pesan_kosong}")
                    return pesan_kosong

                # 2. CABANG SUKSES: Data berhasil ditarik
                elif hasil_csv != "gagal":
                    jam_format = waktu_sekarang.strftime('%H.%M.%S')
                    nama_file_baru = f"Rekap Laporan LCS {waktu_sekarang.strftime('%d-%m-%Y')}{jam_format}.csv"
                    
                    with open(nama_file_baru, "w", encoding="utf-8") as f:
                        f.write(hasil_csv)
                        
                    print(f"[-] File {nama_file_baru} berhasil dibuat. Meneruskan ke Drive...")
                    
                    file_id = upload_ke_drive(nama_file_baru)
                    pesan_sukses = f"Selesai! Data Rekap LCS terbaru berhasil diunggah ke Drive (ID: {file_id})"
                    print(f"🔥 [SUKSES TOTAL] {pesan_sukses}")
                    return pesan_sukses
                    
                # 3. CABANG GAGAL: Elemen tabel belum selesai di-render
                else:
                    print("[-] Notifikasi: Ekstraksi gagal (tabel belum render), mencoba kembali...")
                    continue

    finally:
        print("[-] Menutup sesi aman browser.")
        try:
            driver.quit()
        except:
            pass