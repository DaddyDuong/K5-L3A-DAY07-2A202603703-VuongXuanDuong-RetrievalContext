# Agent dev — so sánh ba cấu hình

**Nhãn do Codex đối chiếu nguồn, đang ở dạng sơ bộ; chưa được học viên xác nhận.**

| Config | Grounded answer tổng /30 | Citation support | Context evidence | Abstention | Median s | API USD | Errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 29/30 | 29/31 | 15/15 | 2/2 | 4.52 | 0.00225033 | 0 |
| english | 28/30 | 26/28 | 15/15 | 2/2 | 4.02 | 0.00238724 | 0 |
| relevance | 28/30 | 25/28 | 15/15 | 2/2 | 4.07 | 0.00221805 | 0 |

Chọn trên dev theo nhãn sơ bộ và tiêu chí công bố trước: **baseline**.
Không chạy test. Grounded answer và citation support cần học viên đọc lại; không phải nhãn do người học đã xác nhận.
Latency là wall time của từng case với 3 worker, gồm chờ khóa retrieval; không dùng để suy rộng benchmark phần cứng.
Context Evidence Rate dùng đầy đủ primary hoặc alternative evidence sau chuẩn hóa whitespace, không suy từ câu trả lời.
Access for free at openstax.org. Đoạn sách trong trace theo CC BY-NC-SA 4.0.
