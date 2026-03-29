ASTAR TRAFFIC HCMC ROUTING - HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY CHƯƠNG TRÌNH

1. YÊU CẦU HỆ THỐNG

- Python 3.8 hoặc cao hơn
- pip (trình quản lý gói Python)
- Windows, macOS, hoặc Linux

2. DANH SÁCH GÓI PHẦN MỀM ĐƯỢC SỬ DỤNG

- streamlit (1.28.0+): Framework phát triển ứng dụng web
- pandas (1.5.0+): Thư viện xử lý dữ liệu
- folium (0.14.0+): Thư viện tạo bản đồ tương tác
- streamlit-folium (0.7.0+): Tích hợp folium với streamlit
- shapely (2.0.0+): Thư viện xử lý hình học không gian
- scipy (1.10.0+): Thư viện tính toán khoa học
- osmnx (1.7.0+): Thư viện xử lý dữ liệu OpenStreetMap

3. CÀI ĐẶT

Bước 1: Tải source code

Sao chép repository hoặc giải nén file dự án

Bước 2: Tạo môi trường ảo (Virtual Environment)

Mở terminal tại thư mục dự án và chạy lệnh:

Windows:
  python -m venv venv
  venv\Scripts\activate

Linux/macOS:
  python3 -m venv venv
  source venv/bin/activate

Bước 3: Cài đặt các gói phần mềm

Chạy lệnh sau để cài đặt tất cả các thư viện cần thiết:

  pip install -r requirements.txt

Quá trình cài đặt sẽ tải và cài đặt tất cả gói được liệt kê trong file requirements.txt

4. BIÊN DỊCH

Chương trình được viết bằng Python, không cần biên dịch trước. Các module sẽ được nạp khi chương trình chạy.

Để kiểm tra cài đặt đúng, chạy:
  python -c "import streamlit; import pandas; import folium; print('Cài đặt thành công')"

Nếu không có lỗi, tất cả thư viện đã được cài đặt đúng.

5. CẤU TRÚC DỮ LIỆU

Dữ liệu được lưu trong thư mục data/:

data/original/: Chứa file OSM (OpenStreetMap) gốc và file huấn luyện
  - hcm_map1.osm, hcm_map2.osm, hcm_map3.osm, hcm_map4.osm: Dữ liệu bản đồ
  - oritrain.csv: Dữ liệu mức độ tắc đường (LOS - Level of Service)

data/processed/: Chứa dữ liệu đã xử lý
  - nodes.csv: Danh sách các nút (giao lộ) với tọa độ
  - edges.csv: Danh sách các cạnh (đoạn đường) với trọng số theo thời gian
  - edges_raw.csv: Dữ liệu cạnh thô trước khi xử lý
  - train.csv: Dữ liệu LOS được xử lý

Ghi chú: Nếu data/processed/ không có dữ liệu, chạy notebook DataPreprocessing.ipynb để xử lý dữ liệu gốc.

6. CHẠY CHƯƠNG TRÌNH

Bước 1: Đảm bảo môi trường ảo đã được kích hoạt

Windows:
  venv\Scripts\activate

Linux/macOS:
  source venv/bin/activate

Bước 2: Chạy ứng dụng

Từ thư mục gốc của dự án, chạy:

  python src/main.py

Hoặc chạy trực tiếp:

  streamlit run src/app.py

Bước 3: Truy cập ứng dụng

Ứng dụng sẽ tự động mở trong trình duyệt tại địa chỉ:
  http://localhost:8501

Nếu không tự động mở, mở trình duyệt và nhập địa chỉ trên.

7. CHỨC NĂNG CHÍNH

Ứng dụng so sánh ba thuật toán tìm đường tối ưu trên bản đồ TP. Hồ Chí Minh:

- Dijkstra: Thuật toán tìm đường ngắn nhất cơ bản
- A*: Thuật toán tìm đường với heuristic Euclidean
- DWA*: Thuật toán tìm đường với heuristic động (Dynamic Weighted A*)

8. CẤU TRÚC THƯ MỤC

src/
  app.py: Mã nguồn ứng dụng Streamlit chính
  main.py: Điểm khởi động chương trình
  load_graph.py: Hàm tải dữ liệu đồ thị từ file CSV
  algorithms/: Thư mục chứa các thuật toán
    - Dijkstra.py: Cài đặt thuật toán Dijkstra
    - AStarOrigin.py: Cài đặt thuật toán A*
    - DWAStar.py: Cài đặt thuật toán DWA*

data/
  original/: Dữ liệu gốc từ OpenStreetMap
  processed/: Dữ liệu đã xử lý
  notebooks/: Notebook Jupyter để xử lý dữ liệu
    - DataPreprocessing.ipynb: Tiền xử lý dữ liệu
    - EDA.ipynb: Phân tích khám phá dữ liệu

static/
  style.css: Tệp tùy chỉnh giao diện

9. XỬ LÝ SỰ CỐ

Lỗi: "ModuleNotFoundError" khi chạy chương trình
Giải pháp: Kiểm tra môi trường ảo đã kích hoạt. Chạy lại: pip install -r requirements.txt

Lỗi: "No such file or directory: data/processed/nodes.csv"
Giải pháp: Chạy notebook DataPreprocessing.ipynb để tạo dữ liệu xử lý

Lỗi: "Port 8501 already in use"
Giải pháp: Chạy: streamlit run src/app.py --server.port 8502

Lỗi: Ứng dụng mở chậm
Giải pháp: Đây là hành vi bình thường với lần chạy đầu tiên. Dữ liệu sẽ được cache lại.

10. LƯU Ý BỔ SUNG

- Ứng dụng yêu cầu kết nối internet để tải bản đồ nền từ OpenStreetMap
- Dữ liệu cache được lưu trong thư mục .streamlit mục đích tăng tốc độ
- Khi dừng ứng dụng, nhấn Ctrl+C ở terminal
