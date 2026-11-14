# Trạng thái bài Day 7

Học viên: **Vương Xuân Dương — 2A202603703 — K5-L3A**.

## Đã chuẩn bị tại workspace

- [x] Dense Day 6, TF-IDF và hybrid RRF trên cùng 252 chunk C.
- [x] Agent model thật, context budget, citation, explicit abstention và trace lỗi.
- [x] Benchmark 24 câu: dev 15+2, test mới 5+2; nguồn/trang/evidence và absence audit.
- [x] So sánh ba retriever, hai thí nghiệm agent cải thiện, phân tích lỗi và chọn trên dev.
- [x] Khóa code/config/cases/nhãn trước test; đánh giá test không chỉnh theo kết quả.
- [x] Trace, kết quả, chi phí và nhãn có lý do; giữ cả các run lỗi.
- [x] Báo cáo cá nhân và hướng dẫn tái lập, dependencies/corpus/model versions.
- [x] 34/34 unit tests pass; kiểm tra database/model thật và test freeze không đổi.

## Việc người học cần hoàn tất khi nộp

- [ ] Đọc, hiểu và xác nhận nhãn/báo cáo. Tất cả review Day 7 hiện là Codex draft;
  không có xác nhận của học viên được ghi thay.
- [x] Repo cá nhân (fork, public):
  https://github.com/DaddyDuong/K5-L3A-DAY07-2A202603703-VuongXuanDuong-RetrievalContext
  — `origin` trỏ về repo này, repo đề bài là `upstream`; không push lên upstream.
- [x] Repo Day 6 public, commit `77fa9c4` có trên `origin/main`.
- [ ] Nộp link repo theo hướng dẫn giảng viên.

Kết quả test sơ bộ: Hit@1 4/5, Hit@3/context 5/5, grounded answer 10/10,
citation support 15/15, abstention 2/2. Baseline=selected dùng chung 7 trace,
không phải hai run độc lập. Không cam kết điểm chấm lab từ các tỷ lệ này.

Không thực hiện bonus tài liệu 100 trang. Không có API key/.env trong bài nộp.
Xem [báo cáo](report/individual/2A202603703_VuongXuanDuong.md),
[tái lập](REPRODUCE.md) và [test](artifacts/agent-test/README.md).

Bài làm được giữ trực tiếp trong repository, gồm code, benchmark, lịch sử
kết quả và báo cáo. Không tạo file ZIP. Pipeline/corpus Day 6 là dependency
ngoài repo Day 7, có repo/commit và cách dựng trong REPRODUCE.md.
