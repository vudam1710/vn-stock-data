# Hướng dẫn Setup GitHub Actions — VN Stock Daily Fetch

Máy không cần bật. GitHub chạy script trên server của họ mỗi ngày, tự commit data vào repo.

---

## Cấu trúc repo

```
github_actions/               ← đây là GitHub repo root
├── .github/
│   └── workflows/
│       └── daily_fetch.yml   ← lịch chạy tự động
├── ai_analyst/               ← agent phân tích (giữ nguyên cấu trúc)
├── data/
│   └── stock_data.csv        ← tự động tạo sau lần chạy đầu
├── reports/                  ← HTML report hàng ngày
├── CLAUDE.md                 ← instructions cho agent
├── config.yaml               ← cấu hình tickers, nguồn data
├── fetch_stock.py            ← script kéo data
└── requirements.txt
```

> Muốn thêm/bớt mã cổ phiếu hoặc đổi cấu hình → **chỉ sửa `config.yaml`**.

---

## Bước 1 — Tạo repo mới trên GitHub

1. Vào https://github.com → click **"New"**
2. Điền:
   - **Repository name**: `vn-stock-data` (hoặc tên bất kỳ)
   - **Visibility**: `Private` (khuyến nghị)
3. Click **"Create repository"**

---

## Bước 2 — Upload files lên repo

Upload toàn bộ nội dung folder `github_actions/` lên repo, giữ đúng cấu trúc thư mục.

**Cách nhanh nhất — dùng Git:**

```bash
cd "path/to/github_actions"
git init
git remote add origin https://github.com/your-username/vn-stock-data.git
git add .
git commit -m "initial setup"
git push -u origin main
```

**Nếu không dùng Git — upload thủ công:**

File `daily_fetch.yml` cần tạo đúng đường dẫn:
1. Click **"Add file"** → **"Create new file"**
2. Gõ tên: `.github/workflows/daily_fetch.yml` (gõ `/` để tạo thư mục)
3. Copy nội dung file vào → **"Commit changes"**

Các file còn lại upload qua **"Add file"** → **"Upload files"**.

---

## Bước 3 — Cấp quyền write cho Actions

1. Vào **Settings** → **Actions** → **General**
2. Kéo xuống **Workflow permissions**
3. Chọn **"Read and write permissions"** → **Save**

> Bước này bắt buộc để Actions có thể commit `stock_data.csv` vào repo.

---

## Bước 4 — Test chạy thủ công lần đầu

1. Vào tab **"Actions"**
2. Click **"VN Stock Daily Fetch"** ở cột trái
3. Click **"Run workflow"** → **"Run workflow"**
4. Chờ ~2 phút → kiểm tra tab **"Code"** có thư mục `data/stock_data.csv` chưa

Lần đầu chạy sẽ fetch **30 ngày gần nhất** (~300 dòng).

---

## Bước 5 — Chạy agent phân tích (local)

Sau khi có data, mở Claude Code và chạy:

```bash
cd "path/to/github_actions"
claude
```

Nói: **"chạy phân tích hôm nay"** — agent tự đọc `CLAUDE.md`, xử lý data, tạo report tại `reports/stock_report_YYYY-MM-DD.html`.

---

## Lịch chạy tự động

Data fetch tự động lúc **18:00 giờ Việt Nam, thứ 2 đến thứ 6**.

> GitHub Actions dùng UTC. Lịch trong `daily_fetch.yml` là `0 11 * * 1-5` (11:00 UTC = 18:00 ICT).

---

## Tùy chỉnh

| Muốn thay đổi | Sửa file |
|---|---|
| Thêm/bớt mã cổ phiếu | `config.yaml` → `tickers` |
| Số ngày fetch lần đầu | `config.yaml` → `fetch.lookback_days` |
| Nguồn data | `config.yaml` → `fetch.source` |
| Giờ chạy tự động | `.github/workflows/daily_fetch.yml` → `cron` |

---

## Troubleshooting

### Actions không chạy tự động
Repo private free có giới hạn 2000 phút/tháng. Script chạy ~2 phút/ngày → ~40 phút/tháng, hoàn toàn trong giới hạn. Kiểm tra tab Actions xem có lỗi không.

### Lỗi permission khi commit CSV
Làm lại Bước 3 — cấp "Read and write permissions".

### Script báo "Data đã up-to-date"
Bình thường — không có ngày mới cần fetch (cuối tuần hoặc ngày lễ).
