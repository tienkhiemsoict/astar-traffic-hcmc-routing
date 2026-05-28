# ASTAR Traffic HCMC Routing

Ứng dụng thuật toán DWA* tìm đường tối ưu trên bản đồ TP. Hồ Chí Minh

## Mục lục

- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Gói phần mềm](#gói-phần-mềm)
- [Cài đặt](#cài-đặt)
- [Chạy chương trình](#chạy-chương-trình)
- [Cấu trúc dữ liệu](#cấu-trúc-dữ-liệu)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)

---

## Yêu cầu hệ thống

- Python 3.8 trở lên
- pip (trình quản lý gói Python)
- Windows, macOS hoặc Linux

---

## Gói phần mềm

| Gói | Phiên bản | Mô tả |
|-----|-----------|-------|
| fastapi | 0.104.0+ | Framework web API |
| uvicorn | 0.24.0+ | ASGI server |
| pandas | 2.0.0+ | Thư viện xử lý dữ liệu |
| numpy | 1.24.0+ | Thư viện tính toán số |
| scipy | 1.11.0+ | Thư viện tính toán khoa học |
| shapely | 2.0.0+ | Thư viện xử lý hình học không gian |
| pydantic | 2.5.0+ | Thư viện validate dữ liệu |
| osmnx | 1.7.0+ | Thư viện xử lý dữ liệu OpenStreetMap |

---

## Cài đặt

### Bước 1: Tải source code

Sao chép repository hoặc giải nén file dự án

### Bước 2: Tạo môi trường ảo

Mở terminal tại thư mục dự án và chạy lệnh:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Bước 3: Cài đặt các gói phần mềm

```bash
pip install -r requirements.txt
```

---

## Chạy chương trình

### Bước 1: Kích hoạt môi trường ảo

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

### Bước 2: Chạy ứng dụng

Từ thư mục gốc dự án, chạy lệnh:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Ứng dụng web sẽ mở tại: `http://127.0.0.1:5500/src/index.html`

---

## Cấu trúc dữ liệu

### data/original/

Chứa dữ liệu gốc từ OpenStreetMap và dữ liệu huấn luyện:

- `hcm_map1.osm`, `hcm_map2.osm`, `hcm_map3.osm`, `hcm_map4.osm` - Dữ liệu bản đồ
- `oritrain.csv` - Dữ liệu mức độ tắc đường (LOS - Level of Service)

### data/processed/

Chứa dữ liệu đã xử lý:

- `nodes.csv` - Danh sách nút (giao lộ) với tọa độ
- `edges.csv` - Danh sách cạnh (đoạn đường) với trọng số theo thời gian
- `edges_raw.csv` - Dữ liệu cạnh thô trước khi xử lý
- `train.csv` - Dữ liệu LOS được xử lý

---

## Cấu trúc thư mục

```
astar-traffic-hcmc-routing/
├── src/
│   ├── web/
│   │   ├── index.html            # Giao diện web
│   │   ├── app.js                # Ứng dụng frontend chính
│   │   └── style.css             # Tùy chỉnh giao diện
│   ├── load_graph.py             # Tải dữ liệu đồ thị
│   └── algorithms/
│       ├── Dijkstra.py           # Thuật toán Dijkstra
│       ├── AStarOrigin.py         # Thuật toán A*
│       └── DWAStar.py             # Thuật toán DWA*
├── data/
│   ├── original/                 # Dữ liệu gốc OSM
│   ├── processed/                # Dữ liệu đã xử lý
│   └── notebooks/
│       ├── DataPreprocessing.ipynb    # Tiền xử lý dữ liệu
│       └── EDA.ipynb                  # Phân tích khám phá dữ liệu
├── assets                          # Hình ảnh và tài nguyên
├── main.py                       # Backend FastAPI chính
└── requirements.txt              # Danh sách gói phần mềm
```
