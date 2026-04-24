# Fitur VNF dan Simulasi Load Balancer

Dokumen ini menjelaskan fungsi fitur VNF, skenario simulasi banyak request, load balancer, serta alur kerja stop VNF pada aplikasi Web-Based SDN + NFV Orchestrator.

## Tujuan Fitur

Fitur ini dibuat untuk mendemonstrasikan bagaimana orchestrator mengatur service function dalam jaringan SDN/NFV.

Secara konsep, aplikasi dapat:

- Menjalankan VNF seperti Firewall, IDS, dan Load Balancer.
- Mengarahkan traffic melalui VNF tertentu dengan policy SDN.
- Mensimulasikan kondisi banyak request dari client.
- Menampilkan bagaimana request tersebut dibagi oleh load balancer ke beberapa backend server simulasi.
- Menghentikan VNF yang sudah berjalan tanpa harus menghentikan topology Mininet.

## Komponen Utama

### 1. Topology

Topology adalah jaringan virtual yang dijalankan dengan Mininet dan Open vSwitch.

Node utama:

- `h1`: client edge atau sumber traffic.
- `s1`: ingress switch.
- `s2`: egress switch.
- `h2`: application host atau server tujuan.
- `fw`: Firewall VNF.
- `ids`: IDS VNF.
- `lb`: Load Balancer VNF.

Topology mengatur jaringan data plane. Tombol `Stop Topology` hanya menghentikan jaringan Mininet, bukan container VNF Docker.

### 2. VNF

VNF adalah Virtual Network Function, yaitu fungsi jaringan yang dijalankan sebagai container Docker.

VNF yang tersedia:

- `fw`: Firewall.
- `ids`: Intrusion Detection System.
- `lb`: Load Balancer.

Fungsi tombol deploy:

- `Deploy Firewall`: menjalankan container `fw`.
- `Deploy IDS`: menjalankan container `ids`.
- `Deploy Load Balancer`: menjalankan container `lb`.

Fungsi tombol stop:

- `Stop Firewall`: menghentikan dan menghapus container `fw`.
- `Stop IDS`: menghentikan dan menghapus container `ids`.
- `Stop Load Balancer`: menghentikan dan menghapus container `lb`.

Di halaman Infrastructure, setiap VNF yang sedang running juga memiliki tombol `Stop` pada daftar VNFs.

### 3. Policy SDN

Policy menentukan jalur traffic yang akan dipasang ke controller Ryu sebagai flow OpenFlow.

Contoh policy:

- `direct`: `h1 -> s1 -> s2 -> h2`
- `firewall`: `h1 -> s1 -> fw -> s1 -> s2 -> h2`
- `ids`: `h1 -> s1 -> ids -> s1 -> s2 -> h2`
- `load_balancer`: `h1 -> s1 -> lb -> s1 -> s2 -> h2`
- `firewall_then_ids`: `h1 -> s1 -> fw -> s1 -> ids -> s1 -> s2 -> h2`

Saat policy diterapkan, backend akan:

1. Mengecek switch yang terhubung ke Ryu.
2. Menyiapkan VNF yang dibutuhkan.
3. Menghapus flow policy lama.
4. Memasang flow baru sesuai path policy.
5. Menyimpan status policy aktif untuk dashboard.

## Simulasi Load Balancer Request Spike

Tombol `Simulate LB Request Spike` digunakan untuk mensimulasikan banyak request yang masuk ke server dan ditangani oleh load balancer.

Saat tombol ini ditekan, sistem melakukan alur berikut:

1. Backend menerima request ke endpoint:

   ```bash
   POST /api/scenario/trigger
   ```

   Payload:

   ```json
   {
     "scenario": "load_balancer_spike",
     "requests": 240,
     "clients": 24
   }
   ```

2. Orchestrator menerapkan policy `load_balancer`.

3. Jika VNF `lb` belum running, orchestrator menjalankan container load balancer terlebih dahulu.

4. Flow SDN diarahkan ke path:

   ```text
   h1 -> s1 -> lb -> s1 -> s2 -> h2
   ```

5. Backend membuat simulasi 240 request dari 24 client.

6. Request dibagi ke tiga backend server simulasi:

   - `app-01`
   - `app-02`
   - `app-03`

7. Algoritma pembagian yang digunakan adalah `round_robin`.

8. Dashboard menampilkan ringkasan:

   - Total request.
   - Jumlah client.
   - Peak RPS.
   - Dropped request.
   - Distribusi request per backend.
   - Estimasi latency per backend.

Contoh hasil untuk 240 request:

```text
app-01: 80 request
app-02: 80 request
app-03: 80 request
```

## Catatan Penting Tentang Simulasi

Load balancer pada fitur ini adalah simulasi orchestration dan telemetry.

Artinya:

- Policy SDN benar-benar diarahkan melalui node/VNF `lb`.
- Container `lb` benar-benar dikelola sebagai VNF Docker.
- Dashboard benar-benar menampilkan status policy, VNF, dan distribusi request.
- Tetapi distribusi request ke `app-01`, `app-02`, dan `app-03` masih berupa simulasi backend, bukan traffic HTTP nyata ke beberapa container server.

Jika ingin membuat load balancer benar-benar menangani HTTP request nyata, perlu tambahan:

- Beberapa container backend server nyata.
- Konfigurasi Nginx atau HAProxy pada container `lb`.
- Routing/networking container agar `lb` bisa mencapai semua backend server.
- Test traffic nyata menggunakan `curl`, `ab`, `wrk`, atau tool sejenis.

## Alur Kerja Dari Dashboard

### Alur Normal Load Balancer

1. Buka halaman Topology.
2. Klik `Start Topology`.
3. Klik `Deploy Load Balancer`, atau langsung klik `Simulate LB Request Spike`.
4. Jika langsung menjalankan scenario, orchestrator akan auto-deploy `lb`.
5. Klik `Simulate LB Request Spike`.
6. Sistem menerapkan policy load balancer.
7. Dashboard menampilkan path aktif melalui `lb`.
8. Halaman Infrastructure menampilkan hasil distribusi request.

### Alur Stop VNF

1. Buka halaman Topology atau Infrastructure.
2. Untuk stop cepat, gunakan tombol:

   - `Stop Firewall`
   - `Stop IDS`
   - `Stop Load Balancer`

3. Atau buka halaman Infrastructure dan klik tombol `Stop` pada VNF yang sedang running.
4. Backend memanggil endpoint:

   ```bash
   POST /api/vnf/stop
   ```

   Contoh payload:

   ```json
   {
     "name": "lb"
   }
   ```

5. Docker container VNF dihentikan dan dihapus.
6. Dashboard refresh status VNF.

## Endpoint yang Terlibat

### Deploy VNF

```bash
POST /api/vnf/deploy
```

Contoh:

```json
{
  "name": "lb",
  "role": "load_balancer"
}
```

Fungsi:

- Menjalankan container VNF.
- Jika container sudah ada tapi stopped, container akan dijalankan lagi.
- Jika container belum ada, container baru dibuat.

### Stop VNF

```bash
POST /api/vnf/stop
```

Contoh:

```json
{
  "name": "lb"
}
```

Fungsi:

- Menghentikan container VNF.
- Menghapus container VNF dari Docker.
- Tidak menghentikan topology Mininet.

### Apply Policy

```bash
POST /api/policy/apply
```

Contoh:

```json
{
  "policy": "load_balancer",
  "auto_deploy": true
}
```

Fungsi:

- Menerapkan service chain ke Ryu controller.
- Auto-deploy VNF yang dibutuhkan jika `auto_deploy` bernilai `true`.

### Trigger Scenario Load Balancer

```bash
POST /api/scenario/trigger
```

Contoh:

```json
{
  "scenario": "load_balancer_spike",
  "requests": 240,
  "clients": 24
}
```

Fungsi:

- Mengaktifkan policy `load_balancer`.
- Menjalankan simulasi banyak request.
- Menghasilkan telemetry distribusi request.

### Stats

```bash
GET /api/stats
```

Fungsi:

- Mengambil status topology.
- Mengambil status VNF.
- Mengambil status controller.
- Mengambil active policy.
- Mengambil telemetry load balancer simulation.

## Ringkasan Perbedaan Stop Topology dan Stop VNF

| Aksi | Yang Dihentikan | Yang Tetap Berjalan |
| --- | --- | --- |
| `Stop Topology` | Mininet dan virtual network topology | VNF Docker container |
| `Stop Firewall` | Container `fw` | Topology dan VNF lain |
| `Stop IDS` | Container `ids` | Topology dan VNF lain |
| `Stop Load Balancer` | Container `lb` | Topology dan VNF lain |

Jadi jika VNF masih terlihat running setelah `Stop Topology`, itu normal. Untuk menghentikan VNF, gunakan tombol stop VNF atau endpoint `/api/vnf/stop`.

