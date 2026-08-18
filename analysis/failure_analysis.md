# Failure Analysis — Lab 18: Production RAG

**Nhóm:** Nhóm Bùi Tiến Phát  
**Thành viên:** Bùi Tiến Phát (2A202601861) - Phụ trách toàn bộ (M1, M2, M3, M4, M5)

---

## RAGAS Scores

| Metric | Naive Baseline | Production | Δ |
|--------|---------------|------------|---|
| Faithfulness | 0.8070 | 0.8833 | +0.0763 |
| Answer Relevancy | 0.6398 | 0.7256 | +0.0857 |
| Context Precision | 0.7750 | 0.7917 | +0.0167 |
| Context Recall | 0.8000 | 0.8458 | +0.0458 |

---

## Bottom-5 Failures

### #1
- **Question:** Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?
- **Expected:** Theo chính sách v2024: 15 ngày cơ bản + 3 ngày thâm niên (9÷3=3) = 18 ngày phép. Lương Senior (P3-P4): 20-35 triệu VNĐ/tháng.
- **Got:** Trả lời sai số ngày phép (thường là 13 hoặc 15 ngày) và khoảng lương do bị lẫn lộn giữa các phiên bản chính sách.
- **Worst metric:** Faithfulness (0.00)
- **Error Tree:** Output sai (LLM bị ảo giác) → Context đúng nhưng nhiễu (chứa cả chính sách cũ v2023 và chính sách mới v2024) → Query OK.
- **Root cause:** Tài liệu gốc chứa thông tin của cả chính sách cũ (v2023) và chính sách mới (v2024) chồng chéo nhau. Hệ thống trích xuất được cả hai chính sách và LLM không phân biệt được đâu là thông tin hiện hành/mới nhất để ưu tiên tính toán.
- **Suggested fix:** Cải thiện Prompt cho Generator để luôn ưu tiên thông tin ghi nhãn phiên bản mới nhất (v2024/hiện hành) hoặc thiết lập bộ lọc siêu dữ liệu (metadata filter) để lọc bỏ tài liệu cũ trước khi truy xuất.

### #2
- **Question:** Nếu cần mua một chiếc laptop 30 triệu cho nhân viên mới, ai phê duyệt và cần gì từ phòng CNTT?
- **Expected:** Laptop 30 triệu nằm trong khoảng 5-50 triệu nên cần Giám đốc phòng ban (Director) phê duyệt. Ngoài ra, mua sắm thiết bị CNTT cần có xác nhận cấu hình kỹ thuật từ phòng CNTT trước khi đề xuất. Cần đính kèm ít nhất 3 báo giá vì trên 10 triệu.
- **Got:** Chỉ nêu được người phê duyệt (Giám đốc phòng ban), thiếu ý về phòng CNTT và yêu cầu 3 báo giá do chunking không kết nối được thông tin liên tài liệu.
- **Worst metric:** Context Precision (0.00)
- **Error Tree:** Output thiếu ý → Context bị thiếu thông tin từ tài liệu CNTT (chỉ lấy được tài liệu quy trình mua sắm chung) → Query OK.
- **Root cause:** Thông tin quy trình mua sắm nằm ở tài liệu hành chính, còn yêu cầu CNTT nằm ở tài liệu bảo mật/CNTT riêng biệt. Chunking thông thường (paragraph) không giữ được liên kết chéo giữa các quy trình.
- **Suggested fix:** Áp dụng Parent-Child Chunking hoặc bổ sung Query Expansion để LLM tự tạo ra các truy vấn phụ (sub-queries) hướng về cả phòng CNTT và quy trình mua sắm.

### #3
- **Question:** Nghỉ phép không lương 20 ngày cần ai phê duyệt?
- **Expected:** Nghỉ 16-30 ngày cần phê duyệt của Giám đốc điều hành (CEO). Lưu ý: nghỉ trên 14 ngày không lương, nhân viên phải tự đóng phần bảo hiểm của mình.
- **Got:** Trả lời là Giám đốc bộ phận hoặc phòng nhân sự (HR) phê duyệt (do lấy nhầm mốc nghỉ phép ít ngày hơn).
- **Worst metric:** Answer Relevancy (0.3967)
- **Error Tree:** Output sai → Context đúng (chứa bảng phân cấp phê duyệt nghỉ phép) → Query OK.
- **Root cause:** LLM gặp khó khăn trong việc ánh xạ con số cụ thể "20 ngày" vào khoảng điều kiện "16-30 ngày" trong tài liệu, dẫn đến việc lấy nhầm thông tin phê duyệt của khoảng kế cận.
- **Suggested fix:** Sử dụng kịch bản lập luận Chain-of-Thought trong prompt để LLM từng bước xác định: 20 ngày nằm trong khoảng nào → Khoảng đó yêu cầu ai phê duyệt → Xuất kết quả.

### #4
- **Question:** Có cần kích hoạt xác thực đa yếu tố (MFA) không?
- **Expected:** Có, theo chính sách mật khẩu v2.0 hiện hành, tất cả nhân viên bắt buộc kích hoạt MFA cho email, VPN và hệ thống nội bộ. Chính sách cũ v1.0 không yêu cầu MFA.
- **Got:** Trả lời chung chung hoặc trả lời không bắt buộc theo chính sách cũ v1.0.
- **Worst metric:** Context Recall (0.50)
- **Error Tree:** Output sai/thiếu → Context bị thiếu (chỉ lấy được tài liệu chính sách mật khẩu v1.0 cũ) → Query OK.
- **Root cause:** Thu hồi thông tin dạng dense vector (Dense Search) không khớp tốt giữa từ khóa viết tắt "MFA" và từ khóa tiếng Việt "xác thực đa yếu tố".
- **Suggested fix:** Cải thiện việc nhúng từ điển viết tắt/đồng nghĩa trong quy trình xử lý truy vấn, hoặc kết hợp BM25 (Hybrid Search) với trọng số phù hợp để tìm kiếm từ khóa chính xác tuyệt đối.

### #5
- **Question:** Nhân viên tạm ứng 15 triệu, sau 20 ngày mới thanh toán. Bị phạt bao nhiêu?
- **Expected:** Thời hạn thanh toán là 15 ngày. Quá hạn 5 ngày, bị tính phí 2%/tháng trên 15.000.000 VNĐ = 300.000 VNĐ/tháng (tính pro-rata khoảng 50.000 VNĐ cho 5 ngày).
- **Got:** Trả lời thiếu chi tiết tính phạt hoặc không tìm thấy quy định phạt tạm ứng quá hạn.
- **Worst metric:** Context Recall (0.50)
- **Error Tree:** Output thiếu thông tin phạt → Context thiếu tài liệu quy định tạm ứng tài chính → Query OK.
- **Root cause:** Tài liệu quy định tạm ứng nằm ở dạng scan/bảng biểu phức tạp, việc phân mảnh theo dòng làm mất cấu trúc tính toán của bảng phạt.
- **Suggested fix:** Tích hợp Table Parsing (trích xuất cấu hình bảng) và OCR chất lượng cao cho các file PDF scan hành chính để bảo toàn định dạng bảng tính toán.

---

## Case Study (cho presentation)

**Question chọn phân tích:**  
"Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?"

**Error Tree walkthrough:**  
1. **Output đúng?** → Sai. LLM trả về số ngày phép là 13 ngày (theo chính sách cũ v2023: 12 ngày cơ bản + 1 ngày thâm niên cho 5 năm).
2. **Context đúng?** → Đúng một nửa. Context trích xuất chứa cả tài liệu chính sách v2023 (cũ) và v2024 (mới).
3. **Query rewrite OK?** → OK. Query viết lại hướng đúng mục tiêu ngày phép và lương Senior.
4. **Fix ở bước:** Generator (Prompt Engineering). Cần tinh chỉnh System Prompt của LLM để hướng dẫn rõ ràng: "Nếu gặp thông tin mâu thuẫn giữa các phiên bản chính sách, hãy ưu tiên phiên bản v2024 mới nhất".

**Nếu có thêm 1 giờ, sẽ optimize:**  
- **Metadata Filtering:** Gán nhãn phiên bản chính sách (`version: "v2023"`, `version: "v2024"`) cho các chunk lúc enrich. Khi nhận query, tự động chỉ truy vấn trên các chunk có nhãn `version: "v2024"` để loại bỏ hoàn toàn nhiễu từ tài liệu cũ.
- **Query Expansion & Sub-question Querying:** Tách câu hỏi phức hợp thành hai câu hỏi đơn: "Số ngày phép của Senior 9 năm thâm niên?" và "Khoảng lương Senior?" để tìm kiếm độc lập và chính xác hơn.
