# Kiểm tra luồng agent thật — 2026-11-14

Đây là kiểm tra phát triển, chưa phải benchmark hay nhãn đã được học viên xác nhận.

| Run (UTC) | Kết quả | Model calls | Retrieval calls | Chi phí provider báo (USD) |
|---|---|---:|---:|---:|
| [20261114T082817363843Z](20261114T082817363843Z/trace.json) | error | 1 | 0 | None |
| [20261114T082907636693Z](20261114T082907636693Z/trace.json) | error | 1 | 0 | 4.436e-05 |
| [20261114T082946574008Z](20261114T082946574008Z/trace.json) | answered | 3 | 3 | 0.00025228 |
| [20261114T083040295481Z](20261114T083040295481Z/trace.json) | error | 2 | 2 | 8.097e-05 |
| [20261114T083117988564Z](20261114T083117988564Z/trace.json) | abstain | 4 | 3 | 0.00021642 |

- q01 trả lời đúng khác biệt read/readline, kèm citation ở trang PDF 320 và 339. Codex đã đọc đối chiếu hai chunk được dẫn và kiểm tra citation nằm trong context cuối.
- Câu hỏi về host/port PostgreSQL riêng của lớp K5-L3: agent tìm 3 lượt rồi từ chối, không đoán thông tin kết nối.
- Giữ cả run lỗi: lần đầu provider không hỗ trợ tham số parallel_tool_calls khi yêu cầu require_parameters; đã bỏ tham số này. Lần hai model trả batch search; đã hỗ trợ thực thi tuần tự. Lần thử câu thiếu evidence phát hiện batch vượt số lượt còn lại; đã giới hạn và ghi các lệnh không thực thi.
- 20/20 test offline pass; kiểm tra context budget, citation ID và giới hạn retrieval trên toàn bộ trace thành công.
- API key không xuất hiện trong code/docs/trace; database Day 6 chỉ đọc. Gold không được gửi vào model/retrieval.
- Chi phí trong bảng là số provider trả trong usage, không gồm CPU embedding, phần cứng/mạng; null là chưa có báo giá.
- Cần học viên đọc lại câu trả lời và evidence. Chưa đánh giá test Day 7, chưa triển khai lexical/hybrid hay benchmark đầy đủ.

Access for free at openstax.org. Nội dung sách/chunk theo CC BY-NC-SA 4.0; xem data/README.md của Day 6.
