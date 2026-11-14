# Trạng thái bài Day 7

Học viên: **Vương Xuân Dương — 2A202603703 — K5-L3A**.
Repo nộp bài: https://github.com/DaddyDuong/K5-L3A-DAY07-2A202603703-VuongXuanDuong-RetrievalContext

## Phần cơ bản

- [x] Dense Day 6, TF-IDF và hybrid RRF trên cùng 252 chunk của index C.
- [x] Agent dùng model thật, có context budget, citation, abstention rõ ràng và trace lỗi.
- [x] Benchmark 24 câu: dev 15+2, test mới 5+2; có nguồn, trang, evidence và audit thiếu evidence.
- [x] So sánh ba retriever, hai thí nghiệm cải thiện agent, phân tích lỗi và chọn cấu hình trên dev.
- [x] Khóa code/config/cases/nhãn trước test; không chỉnh hệ thống theo kết quả test.
- [x] Trace, kết quả, chi phí và nhãn có lý do; giữ cả các run lỗi.
- [x] Báo cáo cá nhân, hướng dẫn tái lập, dependencies, corpus và phiên bản model.
- [x] Unit test offline pass, gồm kiểm tra hash file đã freeze và file nhãn đã xác nhận.
- [x] Học viên đã đọc và xác nhận benchmark và nhãn ([xác nhận](artifacts/student_confirmation.json));
  không đổi nhãn nào.
- [x] Repo cá nhân public, fork của repo đề bài; không push lên upstream.
- [x] Repo Day 6 public, commit `77fa9c4` có trên `origin/main`.
- [ ] Nộp link repo theo hướng dẫn giảng viên.

## Kết quả test

Hit@1 4/5, Evidence Hit@3 5/5, context evidence 5/5, grounded answer 10/10,
citation hỗ trợ 15/15, abstention đúng 2/2. Baseline chính là cấu hình được chọn
nên dùng chung 7 trace, không phải hai lần chạy độc lập.

Không làm thử thách nâng cao 100 trang. Không có API key hoặc `.env` trong bài nộp.
Xem [báo cáo](report/individual/2A202603703_VuongXuanDuong.md),
[tái lập](REPRODUCE.md) và [kết quả test](artifacts/agent-test/README.md).
