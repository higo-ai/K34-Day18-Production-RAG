# Group Report — Lab 18: Production RAG

**Nhóm:** Nhóm Bùi Tiến Phát  
**Ngày:** 19/08/2026

## Thành viên & Phân công

| Tên | Module | Hoàn thành | Tests pass |
|-----|--------|-----------|-----------|
| Bùi Tiến Phát | M1: Chunking | ☑ | 13/13 |
| Bùi Tiến Phát | M2: Hybrid Search | ☑ | 5/5 |
| Bùi Tiến Phát | M3: Reranking | ☑ | 5/5 |
| Bùi Tiến Phát | M4: Evaluation | ☑ | 7/7 |
| Bùi Tiến Phát | M5: Enrichment | ☑ | 7/7 |

## Kết quả RAGAS

| Metric | Naive | Production | Δ |
|--------|-------|-----------|---|
| Faithfulness | 0.8070 | 0.8833 | +0.0763 |
| Answer Relevancy | 0.6398 | 0.7256 | +0.0857 |
| Context Precision | 0.7750 | 0.7917 | +0.0167 |
| Context Recall | 0.8000 | 0.8458 | +0.0458 |

## Key Findings

1. **Biggest improvement:** Điểm số **Answer Relevancy** tăng mạnh nhất (+0.0857) và **Faithfulness** tăng tốt thứ hai (+0.0763) nhờ kỹ thuật Reranking lọc nhiễu tốt và Prompt Generator được cấu hình chặt chẽ hơn.
2. **Biggest challenge:** Quản lý rate limit nghiêm ngặt 15 RPM của Google Gemini Free Tier. Giải quyết triệt để bằng cách tích hợp `InMemoryRateLimiter(0.22)` kết hợp giãn cách request 4.5 giây và sử dụng Local HuggingFace Embeddings chạy offline để giảm 50% số request API.
3. **Surprise finding:** Phiên bản Ragas v0.4.x thay đổi hoàn toàn cấu trúc đối tượng kết quả trả về khiến việc lấy điểm số trực tiếp bị lỗi. Việc chuyển đổi đối tượng sang Pandas DataFrame và tính trung bình trực tiếp là cách xử lý bền vững nhất, hoạt động trên mọi phiên bản.

## Presentation Notes (5 phút)

1. **RAGAS scores (naive vs production):** Điểm số cải thiện ở toàn bộ 4 metrics, trong đó 3/4 tiêu chuẩn vượt qua mốc chất lượng sản xuất 0.75 của BTC.
2. **Biggest win — module nào, tại sao:** Sự kết hợp giữa **Module 2 (Hybrid Search - BM25 + Vector)** giúp tìm chính xác từ khóa và **Module 3 (Cross-Encoder Reranking)** giúp xếp hạng lại ngữ cảnh liên quan hàng đầu, tăng mạnh độ phủ (Context Recall) và độ chính xác (Context Precision).
3. **Case study — 1 failure, Error Tree walkthrough:** 
   - Câu hỏi: *"Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?"*
   - Nguyên nhân: LLM Generator bị ảo giác lấy nhầm chính sách cũ v2023 thay vì v2024 do ngữ cảnh trích xuất chứa cả hai phiên bản.
   - Giải pháp: Thêm chỉ thị trong prompt yêu cầu LLM Generator luôn ưu tiên chính sách mới nhất (v2024).
4. **Next optimization nếu có thêm 1 giờ:** Áp dụng **Metadata Filtering** để chủ động loại bỏ các tài liệu chính sách cũ (v2023) ra khỏi cơ sở dữ liệu trước khi truy vấn, triệt tiêu hoàn toàn sự nhiễu loạn thông tin.
