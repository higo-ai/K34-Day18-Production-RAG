# Individual Reflection — Lab 18

**Tên:** Bùi Tiến Phát (MSHV: 2A202601861)  
**Module phụ trách:** Toàn bộ (M1, M2, M3, M4, M5)

---

## 1. Đóng góp kỹ thuật

- **Module đã implement:** M1, M2, M3, M4, M5
- **Các hàm/class chính đã viết:**
  - **M1 (Chunking):** `chunk_semantic()`, `chunk_hierarchical()`, `chunk_structure_aware()` để cắt tài liệu thông minh.
  - **M2 (Retrieval):** `segment_vietnamese()`, `BM25Search`, `DenseSearch`, `reciprocal_rank_fusion()` triển khai Hybrid Search kết hợp BM25 và Vector Search qua giải thuật RRF.
  - **M3 (Rerank):** `CrossEncoderReranker` sử dụng model Cross-Encoder `BAAI/bge-reranker-v2-m3` để tối ưu hóa vị trí tài liệu liên quan ở top đầu.
  - **M4 (Evaluation):** `evaluate_ragas()`, `get_bottom_failures()` để tự động chấm điểm 4 metric của RAGAS và trích xuất lỗi tệ nhất.
  - **M5 (Enrichment):** `summarize_chunk()`, `generate_hypothesis_questions()`, `call_llm()` bổ sung siêu dữ liệu cho các chunk nhằm tăng chất lượng thu hồi thông tin.
- **Số tests pass:** **37/37 passed** (Đạt 100% trong bộ test pytest).

---

## 2. Kiến thức học được

- **Khái niệm mới nhất:** 
  - **Hybrid Search + RRF:** Sự kết hợp hoàn hảo giữa tìm kiếm từ khóa chính xác (BM25) và tìm kiếm ngữ nghĩa sâu (Dense Vector) thông qua thuật toán Reciprocal Rank Fusion (RRF).
  - **Cross-Encoder Reranking:** Sử dụng mô hình Cross-Encoder để chấm điểm cặp (Query, Document) giúp sắp xếp lại kết quả tìm kiếm với độ chính xác vượt bậc so với Bi-Encoder thông thường.
  - **RAGAS Evaluation:** Tự động hóa đánh giá hệ thống RAG mà không cần con người gắn nhãn thủ công qua 4 metric cốt lõi: Faithfulness, Answer Relevancy, Context Precision và Context Recall.
- **Điều bất ngờ nhất:** 
  - Sự thay đổi schema đột ngột của **Ragas v0.4.x** (đối tượng kết quả trả về không còn là dictionary và không hỗ trợ phương thức `.get()`). 
  - Cách giải quyết bất ngờ và bền vững nhất là **chuyển đối tượng kết quả sang Pandas DataFrame rồi tính toán trung bình (`.mean()`) trực tiếp trên các cột dữ liệu**, giúp tương thích 100% với mọi phiên bản Ragas hiện tại và tương lai.
- **Kết nối với bài giảng (slide nào):** Kết nối chặt chẽ với bài giảng "Advanced RAG Techniques", slide về Hybrid Retrieval, Reranking, Document Enrichment và RAG Evaluation (Ragas Framework).

---

## 3. Khó khăn & Cách giải quyết

- **Khó khăn lớn nhất:** 
  1. Giới hạn tần suất gọi API (Rate Limit 429) cực kỳ nghiêm ngặt của Google AI Studio Free Tier (15 RPM - requests mỗi phút) khiến tiến trình chấm điểm Ragas và Enrichment liên tục bị lỗi nghẽn hoặc sập.
  2. Lỗi AttributeError khi parse kết quả của Ragas v0.4.x do thay đổi thư viện gốc.
- **Cách giải quyết:**
  1. Tích hợp bộ giãn cách **`InMemoryRateLimiter(requests_per_second=0.22)`** vào Chat model của Gemini để khống chế RPM luôn dưới 15, kết hợp **`time.sleep(4.5)`** tường minh trong các vòng lặp API và cơ chế retry tự động tăng dần thời gian ngủ khi gặp lỗi 429.
  2. Sử dụng local embedding `sentence-transformers/all-MiniLM-L6-v2` cho Ragas thay vì Google API để tránh lỗi `501 UNIMPLEMENTED` và tiết kiệm 50% số request gửi lên Google AI Studio.
  3. Sử dụng DataFrame để tính toán điểm số trung bình thay vì truy xuất thuộc tính trực tiếp của đối tượng Ragas.
- **Thời gian debug:** Khoảng 4 giờ.

---

## 4. Nếu làm lại

- **Sẽ làm khác điều gì:** 
  - Sẽ tích hợp thêm bộ lọc Metadata (Metadata Filtering) trước khi thực hiện Retrieval. Việc này giúp hệ thống tự động loại bỏ các tài liệu phiên bản cũ (v2023) ra khỏi ngữ cảnh, giúp LLM Generator không bao giờ bị nhầm lẫn thông tin.
- **Module nào muốn thử tiếp:** 
  - Module 1 (Chunking): Thử nghiệm thêm giải pháp **Layout-Aware Chunking** (sử dụng thư viện Unstructured hoặc PyMuPDF để nhận diện chính xác cấu trúc bảng biểu, tiêu đề) để bảo toàn định dạng bảng tính toán phạt tạm ứng hoặc bảng lương thử việc.

---

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 5/5 |
| Code quality | 5/5 |
| Problem solving | 5/5 |
