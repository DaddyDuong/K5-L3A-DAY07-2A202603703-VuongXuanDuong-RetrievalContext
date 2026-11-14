# Kết quả test mới sau khi khóa cấu hình

**Nhãn do Codex đọc đối chiếu nguồn, chưa được học viên xác nhận.**

| Cấu hình thực thi | Hit@1 | Evidence Hit@3 | Context evidence | Grounded answer | Citation support | Abstention | API USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 4/5 | 5/5 | 5/5 | 10/10 | 15/15 | 2/2 | 0.00142665 |

Baseline và selected trỏ cùng trace vì cấu hình chọn trên dev chính là baseline. Đây là 7 câu và một cấu hình thực thi, không phải hai lần đánh giá độc lập.
Gold/answer labels chỉ dùng sau khi agent kết thúc. Không chỉnh code, prompt hoặc cấu hình theo kết quả test.
Test có câu hỏi mới nhưng dùng chung corpus; không phải holdout tách theo tài liệu.
Chi phí do provider báo, chưa tính phần cứng/điện. Không suy rộng từ 7 câu hoặc coi đây là benchmark nâng cao.
Access for free at openstax.org. Nội dung chunk/evidence theo CC BY-NC-SA 4.0.
