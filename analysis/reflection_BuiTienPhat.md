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
  - **Cross-Encoder Reranking:** Sử dụng mô hình Cross-Encoder để chấm điểm cặp (Query, Document) giúp xếp hạng lại kết quả tìm kiếm với độ chính xác vượt bậc so với Bi-Encoder thông thường.
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

---

## 6. Mapping bài giảng & Action Plan (Theo yêu cầu chi tiết ASSIGNMENT.md)

### Phần 1: Mapping bài giảng

| Lecture Concept | Module | Hàm cụ thể | Observation |
|----------------|--------|-------------|-------------|
| Semantic chunking | M1 | `chunk_semantic()` | Threshold 0.85 tạo ra phân mảnh tập trung đúng chủ đề, ít bị chặt đứt câu giữa chừng so với basic chunking. |
| BM25 + Dense fusion | M2 | `reciprocal_rank_fusion()` | RRF giải quyết vấn đề không đồng nhất giữa điểm số của BM25 (tần suất từ khóa) và Dense (khoảng cách cosine). |
| Cross-encoder reranking | M3 | `CrossEncoderReranker.rerank()` | Latency khoảng 150-200ms trên CPU nhưng đưa tài liệu chứa thông tin nghỉ phép chính xác lên Top 1. |
| RAGAS 4 metrics | M4 | `evaluate_ragas()` | Faithfulness đạt 88.33% chứng minh việc áp dụng Enrichment và Reranking giúp giảm thiểu ảo giác của LLM. |
| Contextual embeddings | M5 | `contextual_prepend()` | Thêm ngữ cảnh tên file tài liệu gốc vào đầu chunk giúp giảm thiểu sai sót khi truy vấn các chính sách chồng chéo. |

### Phần 2: Action Plan cho project

#### Project: Hệ thống RAG tra cứu văn bản và chính sách nhân sự nội bộ doanh nghiệp

#### Hiện tại
- RAG pipeline hiện tại: Sử dụng basic paragraph chunking + Dense Search đơn giản trên cơ sở dữ liệu Vector, gửi trực tiếp context sang LLM gpt-3.5-turbo.
- Known issues: LLM hay trả lời nhầm lẫn giữa quy định cũ và mới; độ chính xác khi tìm kiếm từ khóa chuyên ngành viết tắt (MFA, VPN) rất thấp.

#### Plan áp dụng
1. **Chunking strategy:** Áp dụng Hierarchical Chunking (Parent-Child) để lưu giữ ngữ cảnh đầy đủ của chương chính sách trong khi vẫn đảm bảo độ chính xác khi tìm kiếm đoạn nhỏ.
2. **Search:** Chuyển sang Hybrid Search (BM25 + Dense Vector) qua thuật toán RRF để khắc phục lỗi tìm kiếm từ viết tắt chuyên ngành.
3. **Reranking:** Tích hợp Cross-Encoder Reranker (`bge-reranker-v2-m3`) để lọc nhiễu top-20 tài liệu xuống top-3 trước khi đưa vào LLM.
4. **Evaluation:** Sử dụng khung đánh giá RAGAS để đo đạc định kỳ 4 metrics sau mỗi chu kỳ cập nhật tài liệu mới.
5. **Enrichment:** Sử dụng kỹ thuật Contextual Prepend (đính kèm cấu trúc tiêu đề) và sinh câu hỏi giả định (Hypothetical Questions) để tăng độ phủ ngữ cảnh.

#### Timeline
- **Tuần 1:** Cấu trúc lại dữ liệu, viết script chunking và tạo index Qdrant với Hybrid Search.
- **Tuần 2:** Lập trình phần Reranking, tinh chỉnh prompt và kết hợp LLM Generator.
- **Tuần 3:** Viết pipeline test tự động và chạy RAGAS để đánh giá sản phẩm trước khi golive.
