# 🌐 Web-Based SDN + NFV Orchestrator
**Dynamic Service Chaining Prototype for Academic**

Proyek ini adalah prototipe komprehensif yang mengintegrasikan konsep **Software-Defined Networking (SDN)** dan **Network Function Virtualization (NFV)**. Proyek ini dilengkapi dengan Web Dashboard (GUI) berstandar *Enterprise* untuk mengontrol dan memonitor arsitektur jaringan secara *real-time* tanpa harus selalu bergantung pada terminal (CLI).

Sistem dirancang secara khusus dengan tingkat **Fault Tolerance (Toleransi Kesalahan)** yang tinggi agar sangat stabil saat didemonstrasikan secara *live* pada saat sidang/UAS.

---

## 🏛️ Arsitektur Sistem Lengkap

Sistem ini terbagi menjadi 5 komponen utama yang bekerja secara terintegrasi:

1. **SDN Controller (Control Plane) — `Ryu`**
   - Bertindak sebagai "otak" jaringan menggunakan protokol OpenFlow 1.3.
   - Menggunakan `ryu_app.py` yang memadukan logika L2 Switch dan mengekspos **REST API** (`ofctl_rest`) untuk injeksi tabel *routing* (Flow Rules) secara dinamis.
   
2. **Network Emulator (Data Plane) — `Mininet & Open vSwitch (OVS)`**
   - Mensimulasikan *Service Path Topology* yang terdiri dari: `Client (h1)`, `Switch (s1 & s2)`, dan `Server (h2)`.
   - Menggunakan fitur **Standalone Mode Fallback**: Topologi dijamin tidak akan *crash* saat dijalankan meskipun Ryu Controller belum dihidupkan.
   - Node VNF (Docker) diintegrasikan secara langsung ke dalam *switch* menggunakan konsep *veth pairs*.

3. **Virtual Network Functions (NFV) — `Docker`**
   - "Layanan Jaringan" (seperti Firewall/Load Balancer) tidak lagi berupa alat fisik yang mahal, melainkan dijalankan secara instan di dalam *container*.
   - **VNF Firewall**: Image berbasis Ubuntu ringan yang digunakan untuk mensimulasikan penyaringan *traffic*.

4. **Orchestrator Backend — `Flask (Python)`**
   - Menjadi jembatan utama (*Middleware*) antara Web GUI dengan Mininet, Docker, dan Ryu.
   - Menggunakan sistem **Safe Cleanup & PID Tracking**: Proses Mininet diatur di latar belakang dengan mekanisme penguncian khusus agar terhindar dari *race condition* (anti-error jika tombol diklik berulang kali) dan pembersihan yang dijamin **tidak** mematikan Controller Ryu secara tak sengaja.

5. **Web Dashboard GUI (Frontend)**
   - UI/UX Premium bergaya *Glassmorphism* menggunakan HTML5, Vanilla JS, CSS3, dan Bootstrap 5.
   - Menampilkan visualisasi topologi yang dinamis dan data *real-time*.

---

## ✨ Fitur-Fitur Utama

* **🚀 One-Click Topology Provisioning**: Membangun dan menghancurkan jaringan secara otomatis dari Web.
* **🐳 On-Demand VNF Deployment**: Menghidupkan *container* fungsi jaringan (Firewall) secara instan via Docker Engine.
* **🔗 Dynamic Service Chaining**: "Membelokkan" arah lalu lintas data (H1 → H2) secara dinamis agar melewati VNF Firewall terlebih dahulu melalui penyuntikan *OpenFlow Rules*.
* **📊 Advanced Telemetry & Metrics**:
  * **Host System Resources**: Memonitor beban CPU dan RAM server fisik secara langsung.
  * **VNF Details**: Menampilkan ID Docker yang sedang aktif bertugas.
  * **Live Event Logger**: Merekam respons *backend* (Sukses/Error) secara historis seperti terminal asli.
* **🔍 OpenFlow Rules Inspector**: Dilengkapi fitur Modal/Pop-up tabel interaktif untuk "mengintip" wujud asli *Routing Table* (Match, Action, Priority, Packets) yang disuntikkan ke dalam Switch oleh SDN Controller.

---

## 🚀 Panduan Menjalankan (Khusus WSL/Ubuntu Linux)

### Langkah 1: Persiapan Environment
Pastikan Anda berada di terminal Ubuntu/WSL. Instal utilitas *system*:
```bash
sudo apt update
sudo apt install -y python3-pip mininet openvswitch-switch docker.io curl
```
*Pastikan daemon Open vSwitch berjalan:* `sudo service openvswitch-switch start`

### Langkah 2: Mengaktifkan Layanan Docker
Jalankan manual Docker *daemon* jika menggunakan WSL:
```bash
sudo service docker start
```
*(Cek dengan `sudo docker ps`. Jika tidak error, artinya Docker siap).*

### Langkah 3: Menginstal Dependensi Python
Arahkan terminal ke root proyek, buat virtual environment, lalu instal dependensi backend:
```bash
cd /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements.txt
```
Dengan cara ini backend bisa dijalankan lewat `sudo` tanpa kehilangan dependency Python.

### Langkah 4: Menjalankan SDN Controller (Terminal 1)
Proyek sekarang mendukung 2 mode controller:

**Opsi A - Local Host (default)**

Buka terminal baru (atau *tab* baru). Masuk ke folder `controller` dan jalankan Ryu Controller:
```bash
cd controller/
~/.local/bin/ryu-manager ryu_app.py ryu.app.ofctl_rest
```
*Tunggu hingga muncul pesan `SDN Controller Started. Waiting for switches...` lalu biarkan terminal ini tetap terbuka.*

**Opsi B - Docker Container**

Mode ini cocok jika instalasi `ryu` lokal bermasalah. Build image lalu jalankan container dengan host networking agar endpoint tetap konsisten:
```bash
cd controller/
docker build -t sdn-ryu-controller .
docker run --rm --name sdn-ryu-controller --network host sdn-ryu-controller
```

Atau langsung dari root project memakai Docker Compose:
```bash
cd /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype
docker compose up --build -d sdn-ryu-controller
```
Jika container bernama `sdn-ryu-controller` aktif, backend akan mendeteksi mode `Docker` secara otomatis untuk tampilan dashboard.

Untuk melihat log controller:
```bash
docker compose logs -f sdn-ryu-controller
```

Untuk menghentikannya:
```bash
docker compose stop sdn-ryu-controller
```

Jika controller Docker dijalankan dengan endpoint selain `127.0.0.1`, export konfigurasi ini sebelum menjalankan backend:
```bash
export SDN_CONTROLLER_MODE=docker
export SDN_CONTROLLER_HOST=<host-atau-ip-controller>
export SDN_CONTROLLER_REST_PORT=8080
export SDN_CONTROLLER_OF_PORT=6653
```
Lalu jalankan backend dengan `sudo -E` agar environment variable tetap diteruskan.

### Langkah 5: Menjalankan Orchestrator Web (Terminal 2)
Di terminal yang lain, masuk ke folder `backend` dan jalankan Flask memakai interpreter dari `.venv`. **Wajib menggunakan `sudo`** karena Flask butuh akses *root* untuk memanipulasi *Network Namespace* dan Docker.
```bash
cd /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype/backend
sudo /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype/.venv/bin/python app.py
```
*Server akan berjalan di port 5000.*

Jika memakai konfigurasi controller non-default dari environment variable, gunakan:
```bash
cd /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype/backend
sudo -E /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype/.venv/bin/python app.py
```

> [!TIP]
> `mininet/topo.py` dan backend sekarang membaca konfigurasi controller dari environment variable yang sama, sehingga mode `local` dan `docker` memakai source code yang sama tanpa perlu edit manual file Python.

> [!IMPORTANT]
> Jika backend dijalankan tanpa `sudo`, endpoint topology akan ditolak lebih awal dengan pesan bahwa operasi Mininet memerlukan hak akses root. Ini memang disengaja agar error-nya jelas dan tidak menunggu crash dari proses `mn`.

### Jalur Cepat: Controller Docker + Backend Lokal
Kalau Anda ingin jalur yang paling stabil berdasarkan pengujian repo ini, pakai kombinasi berikut:
```bash
cd /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype
docker compose up --build -d sdn-ryu-controller

cd /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype/backend
sudo /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype/.venv/bin/python app.py
```

### Langkah 6: Skenario Live Demo untuk Dosen / Presentasi
1. Buka Web Browser, masuk ke alamat: **`http://localhost:5000`**
2. Jelaskan struktur UI, tekankan bahwa bagian **SDN Controller** sudah berstatus `Online`.
3. Klik tombol **🚀 Start Topology** -> *Jelaskan bahwa Data Plane telah terbentuk.*
4. Klik tombol **🛡️ Deploy Firewall (Docker)** -> *Jelaskan konsep **NFV** di mana fungsi jaringan fisik digantikan oleh Container virtual.*
5. Klik tombol **🔗 Install Redirect Flow** -> *Jelaskan konsep **SDN (Service Chaining)** di mana jalur trafik dibelokkan secara otomatis melalui *software* (tanpa memindah kabel fisik).*
6. Klik tombol **🔍 View OpenFlow Table** di sebelah kanan -> *Tunjukkan bukti matematis berupa tabel kepada dosen bahwa aturan (rules) tersebut benar-benar tertanam ke dalam OVS Switch.*

> [!NOTE]
> Jika terjadi *glitch* pada Mininet di tengah pengujian, matikan topologi dari Web GUI, atau secara manual jalankan `sudo mn -c` pada terminal sebelum melakukan demonstrasi ulang.
