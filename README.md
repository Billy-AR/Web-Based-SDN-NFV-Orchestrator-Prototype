# Web-Based SDN + NFV Orchestrator

Proyek ini adalah prototipe orchestrator untuk demonstrasi integrasi SDN dan NFV. Sistem menggabungkan:

- `Ryu` sebagai SDN controller
- `Mininet` dan `Open vSwitch` sebagai emulasi data plane
- `Docker` untuk menjalankan VNF
- `Flask` sebagai backend orchestrator
- web dashboard untuk kontrol dan monitoring

## Arsitektur Singkat

Komponen utama repo ini:

- `controller/`: aplikasi Ryu dan REST API OpenFlow
- `backend/`: backend Flask untuk orchestration, telemetry, dan operasi topology/VNF
- `mininet/`: topologi Mininet yang terhubung ke controller
- `docker-compose.yml`: jalur standar untuk menjalankan controller di Docker

Mode yang direkomendasikan dan didukung repo ini:

- controller di Docker
- backend lokal
- Mininet/Open vSwitch lokal

Backend harus dijalankan dengan `sudo` karena membutuhkan akses root untuk Mininet dan network namespace.

## Tutorial menjalakan dengan Docker di Ubuntu 24+

1. Pastikan dependency sistem sudah ada:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv mininet openvswitch-switch docker.io curl
sudo service openvswitch-switch start
sudo service docker start
```

2. Siapkan virtualenv backend:

```bash
cd /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements.txt
```

3. Jalankan controller via Docker:

```bash
cd /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype
docker compose up --build -d sdn-ryu-controller
```

4. Cek log controller:

```bash
docker compose logs -f sdn-ryu-controller
```

5. Jalankan backend di terminal lain:

```bash
cd /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype/backend
sudo /home/thekingsman/Web-Based-SDN-NFV-Orchestrator-Prototype/.venv/bin/python app.py
```

6. Buka aplikasi:

```bash
http://127.0.0.1:5000/
```

```bash
docker compose ps
```

Catatan penting: backend tetap lokal dan harus dijalankan dengan sudo, karena backend perlu akses root untuk Mininet/network namespace. Jadi mode yang didukung repo ini adalah:

- controller di Docker
- backend lokal
- mininet/openvswitch lokal
