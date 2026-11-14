# So sánh retrieval trên dev

| Method | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Median ms | Errors |
|---|---:|---:|---:|---:|---:|
| dense | 9/15 (60.0%) | 11/15 (73.3%) | 11/15 (73.3%) | 24.21 | 0 |
| lexical | 5/15 (33.3%) | 10/15 (66.7%) | 10/15 (66.7%) | 0.52 | 0 |
| hybrid | 9/15 (60.0%) | 11/15 (73.3%) | 11/15 (73.3%) | 27.65 | 0 |

Chọn tạm trên dev theo tiêu chí công bố trước: **dense**.

Cùng 252 chunk C, cùng query gốc và filter do câu hỏi cung cấp. Không viết lại query, không gọi model trả lời, không đánh giá test. Context Evidence Rate ở đây đo context của một lượt top-3, không phải context nhiều lượt của agent.

Chi phí API retrieval = 0 USD (chạy local); chưa tính phần cứng/điện. Thời gian setup và warmup ghi riêng trong config.json. Timing là một lần đo, có nhiễu.

Gold dùng chỉ ở bước chấm sau retrieval. Strict metric chưa thay đánh giá nguồn thủ công.

Access for free at openstax.org. Nội dung chunk theo CC BY-NC-SA 4.0; nguồn tại hồ sơ Day 6.
