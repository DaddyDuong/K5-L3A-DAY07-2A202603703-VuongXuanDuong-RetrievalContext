# Định dạng dữ liệu

## Benchmark đang dùng trong repo

`dev_cases.json` gồm 15 câu có đáp án giữ nguyên từ dev Day 6 và 2 câu thiếu
bằng chứng (`u01`, `u02`). Các câu có đáp án giữ schema Day 6
(`gold_source_id`, `gold_page`, `evidence_quote`, `alternative_gold`), được
`starter/benchmark_agent_dev.py` chấm trực tiếp; không truyền file này vào
baseline CLI dùng schema `gold` bên dưới nếu chưa chuyển đổi.

`dev_absence_audit.json` ghi SHA-256 corpus, tất cả 52 trang được quét, từ khóa,
trang liên quan và kết luận cho hai câu thiếu bằng chứng. Không dựa vào việc
top-k không tìm thấy để kết luận thiếu thông tin. Nhãn do Codex soạn/đối chiếu,
học viên đã đọc và xác nhận ([xác nhận](../artifacts/student_confirmation.json)). Hai file trên chỉ chứa dev.

`test_cases.json` có 5 câu có đáp án mới và 2 câu thiếu bằng chứng mới, được
chốt sau dev và trước khi chạy test. `test_absence_audit.json` kiểm tra thiếu
bằng chứng trên toàn corpus. Evidence của 5 câu được đối chiếu text layer PDF.
`benchmark.json` ghép hai tập thành 24 câu (20 có đáp án, 4 thiếu evidence),
không đổi nhãn hay schema. Bộ test dùng chung corpus, không tách theo tài liệu.

Access for free at openstax.org. Evidence từ OpenStax theo CC BY-NC-SA 4.0;
giữ attribution theo corpus Day 6.

## Schema starter gốc

Các file `example_*.json` chỉ minh họa định dạng, không đủ để nộp bài. Dữ liệu thật là JSON array UTF-8; nếu dùng định dạng khác, ghi cách chuyển trong README.

- **Chunk:** `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID phải duy nhất; giữ phiên bản hoặc ngày nếu có.
- **Câu có đáp án:** `id`, `split` (`dev` hoặc `test`), `question`, `expected_answer`, `gold`: danh sách `{source_id, page, evidence}`. Với schema mẫu, mỗi evidence phải nằm trọn trong một chunk đúng nguồn và trang; các phần tử `gold` là evidence thay thế. Với câu multi-hop cần nhiều đoạn, bạn có thể mở rộng schema, ghi rõ nhóm evidence bắt buộc và cách chấm. Có thể thêm `filter` do người dùng cung cấp trước.
- **Câu thiếu evidence:** `id`, `split`, `question`, `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`. Xem `agent_cases_example.json`.

Không đưa `gold` hoặc nhãn đáp án vào model và retrieval tool. Ghi nguồn dữ liệu và quyền sử dụng. Cách chuyển một số định dạng Day 6: [starter/README.md](../starter/README.md).
