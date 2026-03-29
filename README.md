# ASTAR Traffic HCMC Routing

Ứng dụng thuật toán DWA* tìm đường tối ưu trên bản đồ TP. Hồ Chí Minh

## Mục lục

- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Gói phần mềm](#gói-phần-mềm)
- [Cài đặt](#cài-đặt)
- [Chạy chương trình](#chạy-chương-trình)
- [Cấu trúc dữ liệu](#cấu-trúc-dữ-liệu)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Xử lý sự cố](#xử-lý-sự-cố)
- [Lưu ý](#lưu-ý)

---

## Yêu cầu hệ thống

- Python 3.8 trở lên
- pip (trình quản lý gói Python)
- Windows, macOS hoặc Linux

---

## Gói phần mềm

| Gói | Phiên bản | Mô tả |
|-----|-----------|-------|
| streamlit | 1.28.0+ | Framework phát triển ứng dụng web |
| pandas | 1.5.0+ | Thư viện xử lý dữ liệu |
| folium | 0.14.0+ | Thư viện tạo bản đồ tương tác |
| streamlit-folium | 0.7.0+ | Tích hợp folium với streamlit |
| shapely | 2.0.0+ | Thư viện xử lý hình học không gian |
| scipy | 1.10.0+ | Thư viện tính toán khoa học |
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

Để kiểm tra cài đặt thành công:

```bash
python -c "import streamlit; import pandas; import folium; print('Cài đặt thành công')"
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

Từ thư mục gốc dự án, chạy một trong các lệnh sau:

```bash
python src/main.py
```

Hoặc:

```bash
streamlit run src/app.py
```

### Bước 3: Truy cập ứng dụng

Ứng dụng sẽ tự động mở trong trình duyệt tại:

```
http://localhost:8501
```

Nếu không tự động mở, mở trình duyệt và nhập địa chỉ trên.

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

**Ghi chú:** Nếu thư mục `data/processed/` không có dữ liệu, chạy notebook `DataPreprocessing.ipynb` để xử lý dữ liệu gốc.

---

## Cấu trúc thư mục

```
astar-traffic-hcmc-routing/
├── src/
│   ├── app.py                    # Ứng dụng Streamlit chính
│   ├── main.py                   # Điểm khởi động
│   ├── load_graph.py             # Tải dữ liệu đồ thị từ CSV
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
├── static/
│   └── style.css                 # Tùy chỉnh giao diện
├── requirements.txt              # Danh sách gói phần mềm
└── README.md                     # Hướng dẫn này
```

---

## Xử lý sự cố

### ModuleNotFoundError khi chạy chương trình

**Giải pháp:** Kiểm tra môi trường ảo đã kích hoạt. Chạy lại:

```bash
pip install -r requirements.txt
```

### "No such file or directory: data/processed/nodes.csv"

**Giải pháp:** Chạy notebook `DataPreprocessing.ipynb` để tạo dữ liệu xử lý.

### "Port 8501 already in use"

**Giải pháp:** Chạy trên cổng khác:

```bash
streamlit run src/app.py --server.port 8502
```

### Ứng dụng mở chậm

**Giải pháp:** Đây là hành vi bình thường với lần chạy đầu tiên. Dữ liệu sẽ được cache lại.

---

## Lưu ý

- Ứng dụng yêu cầu kết nối internet để tải bản đồ nền từ OpenStreetMap
- Dữ liệu được cache trong thư mục `.streamlit` để tăng tốc độ
- Để dừng ứng dụng, nhấn `Ctrl+C` ở terminal
