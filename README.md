🌸 AISYAH - Website Load Tester with Live Dashboard

<div align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-magenta" alt="Version">
  <img src="https://img.shields.io/badge/python-3.7+-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey" alt="Platform">
</div>

<p align="center">
  <b>AISYAH</b> adalah tool load testing website dengan live dashboard real-time yang interaktif dan mudah digunakan.
</p>

📸 Preview Dashboard

```
┌─────────────────────────────────────────┐
│  🌸 AISYAH LIVE DASHBOARD  14:30:25    │
├─────────────────────────────────────────┤
│  📊 SUMMARY                             │
│  Status: ● RUNNING                      │
│  Duration: 45.2s                        │
│  Requests: 1,234                        │
│  ✅ Successful: 1,200                    │
│  ❌ Failed: 34                          │
│  Success Rate: 97.2%                    │
│  RPS: 27.3                              │
├─────────────────────────────────────────┤
│  ⚡ PERFORMANCE                          │
│  Avg Response: 125.3 ms                 │
│  Median Response: 118.7 ms              │
│  Min Response: 45.2 ms                  │
│  Max Response: 312.8 ms                 │
│  95th Percentile: 245.6 ms              │
│  99th Percentile: 302.1 ms              │
├─────────────────────────────────────────┤
│  📋 Status Codes                        │
│  HTTP 200: 1,200 (97.2%)                │
│  HTTP 404: 15 (1.2%)                    │
│  HTTP 500: 19 (1.5%)                    │
├─────────────────────────────────────────┤
│  📈 Response Time History               │
│  [ASCII Chart - Full Width]             │
├─────────────────────────────────────────┤
│  ⚠ ERRORS (5)                          │
│  Connection Error: 3                    │
│  Timeout: 2                             │
└─────────────────────────────────────────┘
```

✨ Fitur Utama

📊 Live Dashboard

· Real-time Monitoring - Update setiap 0.5 detik
· Portrait Mode - Optimal untuk tampilan HP dan layar sempit
· Color Coding - Status warna berdasarkan performa
· Comprehensive Stats - Lengkap dengan percentiles

⚡ Performance Metrics

· Response Time (Min, Max, Avg, Median)
· 95th & 99th Percentiles
· Requests Per Second (RPS)
· Success Rate dengan color indicator

📈 Visual Analytics

· ASCII Chart untuk Response Time History
· Status Code Distribution
· Error Tracking dengan detail

🚀 Quick Start

Prerequisites

```bash
Python 3.7 or higher
pip (Python package manager)
```

Installation

```bash
# Clone repository
git clone https://github.com/yourusername/aisyah.git
cd aisyah

# Install dependencies
pip install -r requirements.txt

# Run AISYAH
python aisyah.py
```

Requirements

```txt
requests>=2.28.0
rich>=13.3.0
plotext>=5.2.0
```

🎯 Cara Penggunaan

Basic Usage

```bash
python aisyah.py
```

Input Parameters

1. URL Website - Masukkan URL yang akan di-test (contoh: https://example.com)
2. Number of Requests - Jumlah total request (default: 100)
3. Concurrent Threads - Jumlah thread paralel (default: 10)

Contoh Sesi

```bash
🌸 AISYAH 🌐 Enter website URL: https://example.com
🌸 AISYAH 📊 Number of requests: 500
🌸 AISYAH ⚡ Concurrent threads: 20
```

Controls

· Ctrl+C - Menghentikan test (akan menampilkan partial report)
· Auto-generate - Report lengkap setelah test selesai

📊 Interpretasi Hasil

Success Rate Indicators

Rate Status Indikasi
≥ 95% 🟢 Excellent Website berjalan sangat baik
80-95% 🟡 Warning Performance perlu improvement
< 80% 🔴 Critical Website mengalami masalah

Response Time Guidelines

Time Kategori
< 200ms ⚡ Excellent
200-500ms 👍 Good
500-1000ms ⚠️ Acceptable
1000ms ❌ Slow

🛠️ Teknologi yang Digunakan

· Python 3.7+ - Core programming language
· Requests - HTTP client library
· Rich - Terminal UI dan formatting
· Plotext - ASCII chart generation
· ThreadPoolExecutor - Concurrent request processing

📁 Struktur Project

```
aisyah/
├── aisyah.py              # Main application
├── requirements.txt       # Dependencies
├── README.md             # Documentation
├── LICENSE               # MIT License
└── .gitignore            # Git ignore file
```

🔧 Advanced Configuration

Custom Headers

Edit AisyahLoadTester class untuk custom headers:

```python
self.session.headers.update({
    'User-Agent': 'Custom-User-Agent',
    'Authorization': 'Bearer your-token',
})
```

Timeout Settings

```python
self.session.timeout = 30  # Change timeout (seconds)
```

🤝 Contributing

Kami sangat menghargai kontribusi! Silakan ikuti langkah-langkah berikut:

1. Fork repository ini
2. Clone fork Anda
3. Buat branch untuk fitur baru (git checkout -b feature/AmazingFeature)
4. Commit perubahan Anda (git commit -m 'Add AmazingFeature')
5. Push ke branch (git push origin feature/AmazingFeature)
6. Open Pull Request

Guidelines

· Ikuti PEP 8 style guide
· Tambahkan docstring untuk fungsi baru
· Update README jika diperlukan
· Test sebelum submit

🐛 Reporting Issues

Jika menemukan bug atau memiliki saran:

1. Cek Issues apakah sudah ada yang melaporkan
2. Buat New Issue dengan deskripsi detail
3. Sertakan:
   · Version AISYAH
   · Python version
   · OS dan version
   · Steps untuk reproduce
   · Expected vs actual behavior

📝 Changelog

v1.0.0 (2024-01-15)

· 🎉 Initial release
· ✨ Live dashboard dengan portrait mode
· 📊 Real-time monitoring
· 📈 ASCII chart untuk response time
· 🎨 Color-coded status indicators
· 🚀 Multi-threading support
· 📱 Optimasi untuk tampilan HP

📄 License

Distributed under the MIT License. See LICENSE for more information.

👨‍💻 Author

AISYAH Team

· GitHub: @yourusername
· Email: your.email@example.com

🙏 Acknowledgments

· Rich - Terminal UI library
· Requests - HTTP library
· Plotext - ASCII plotting

⚠️ Disclaimer

AISYAH adalah tool untuk testing dan monitoring website secara legal. 
Hanya gunakan untuk website yang Anda miliki atau memiliki izin untuk testing.

❌ DILARANG menggunakan untuk:

· DDoS attack
· Unauthorized testing
· Illegal activities

Gunakan dengan bijak dan bertanggung jawab! 🌸

🌟 Star History

https://api.star-history.com/svg?repos=yourusername/aisyah&type=Date

---

<div align="center">
  <sub>Built with ❤️ by AISYAH Team</sub>
  <br>
  <sub>🌸 Made with love for better web testing</sub>
</div>
```

📁 File Requirements

requirements.txt

```txt
requests>=2.28.0
rich>=13.3.0
plotext>=5.2.0
```

