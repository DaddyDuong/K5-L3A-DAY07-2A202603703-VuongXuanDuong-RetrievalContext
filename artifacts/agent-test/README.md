# Test Day 7 — sau khi khóa cấu hình

Run chính thức: [20261114T090432454098Z](20261114T090432454098Z/summary.md).
Xem [summary JSON](20261114T090432454098Z/summary.json),
[7 trace](20261114T090432454098Z/traces.json),
[review từng câu/citation](20261114T090432454098Z/baseline/reviews.json),
[config và alias](20261114T090432454098Z/config.json).

**Nhãn do Codex đọc đối chiếu nguồn; học viên đã đọc và xác nhận sau test, không
đổi nhãn nào ([xác nhận](../student_confirmation.json)).**

## Thiết kế và khóa trước test

- [7 câu mới](../../data/test_cases.json): 5 câu có đáp án về default mode,
  đường dẫn file, CSV, Pandas unique và scatter plot; 2 câu thiếu bằng chứng về
  giải mã AES-256 bằng read_csv và DPI xuất PNG.
- Evidence có trong chunk C, page text và text layer của PDF; không dùng
  retrieval để chọn câu dễ hoặc chỉnh cấu hình. Hai câu thiếu evidence được
  kiểm tra trên toàn bộ 52 trang: [absence audit](../../data/test_absence_audit.json).
- [Rà soát dev trước test](../dev_review_before_test.json) giữ nguyên nhãn
  bảo thủ và lựa chọn baseline; không sửa agent code/prompt.
- [Freeze manifest](../test-freeze.json) giữ SHA-256 của code, model/provider,
  selection, nhãn dev, câu hỏi và corpus snapshot. [Test-start marker](../test_started.json)
  được ghi trước lời gọi retrieval/model đầu tiên. Runner kiểm tra hash trước
  và sau test; tất cả giữ nguyên.

Baseline chính là cấu hình được chọn trên dev, nên `baseline` và `selected`
là hai alias trỏ cùng 7 trace. Không chạy hai lần hoặc nhân đôi mẫu số/chi phí
để tạo cảm giác có hai thí nghiệm độc lập. Cấu hình dense C, top-3, tối đa
3 search, context 4.000 ký tự, query auto, chọn chunk theo thứ tự đến.

## Kết quả

| Chỉ số | n/N | Tỷ lệ |
|---|---:|---:|
| Hit@1 lần tìm đầu | 4/5 | 80% |
| Evidence Hit@3 lần tìm đầu | 5/5 | 100% |
| Evidence trong context cuối | 5/5 | 100% |
| Grounded answer | 10/10 điểm | 100% |
| Citation có trong context và hỗ trợ nội dung | 15/15 | 100% |
| Câu trả lời có citation | 5/5 | 100% |
| Từ chối đúng câu thiếu evidence | 2/2 | 100% |
| Từ chối nhầm câu có đáp án | 0/5 | 0% |
| Dùng retrieval tool | 7/7 | 100% |

Không có lỗi thực thi. Context do Codex chấm, học viên xác nhận: 0 điểm = 0 câu,
1 điểm = 0 câu, 2 điểm = 5 câu. Grounded answer 0/1/2: 0/0/5; trung bình
2,0/2. Nhãn và lý do riêng cho từng câu/citation trong reviews.json.

18 model calls, 13 retrieval calls; 3 câu tìm 1 lượt, 2 câu tìm 2 lượt,
2 câu tìm 3 lượt. Median wall time 4,16 giây/case; tổng wall time từng case
40,41 giây (không phải thời gian batch do chạy 3 worker). Chi phí API provider
báo **0,00142665 USD**, chưa gồm CPU/điện/phần cứng.

## Nhận xét sau test, không dùng để chỉnh hệ thống

`t03` chưa hit ở hạng đầu nhưng evidence có trong top-3. Câu trả lời nêu đúng
newline phân hàng và comma phân ô. Phần thêm về tách hàng bằng comma được xem
là suy luận từ định dạng đã dẫn; code strip/split cũng có trong context. Không
suy ra đây là parser CSV tổng quát xử lý được quoted delimiters/escape.

`t04` đã có evidence ở lần tìm đầu nhưng agent vẫn tìm đủ 3 lượt trước khi trả
lời. Đây là chi phí tool use dư thừa cần ghi nhận, không phải lý do chạy lại
hoặc chỉnh điều kiện dừng sau khi đã xem test. Câu trả lời vẫn đủ nguồn và
không tự khẳng định thứ tự của mảng unique khi chưa có evidence.

`tu01`, `tu02` từ chối đưa tham số/con số không có trong nguồn, chỉ nêu thông
tin nền đã dẫn. Không suy từ việc top-k thất bại ra kết luận toàn bộ tài liệu
không có thông tin: kết luận thiếu evidence có audit corpus riêng trước test.

## Giới hạn

Các câu mới chưa được dùng chỉnh hệ thống, nhưng dùng chung sách/corpus với
dev và có phần tổng kết lặp nội dung. Đây không phải holdout theo tài liệu,
chủ đề hoặc người chấm mù. Bộ test nhỏ, một lần chạy và cùng AI tham gia soạn/
review có thể tạo thiên lệch; không suy rộng chất lượng hay tuyên bố điểm lab.
Không thực hiện thử thách nâng cao 100 trang/90% test.

Runner chặn chạy test chính thức lần nữa. `--reproduction` chỉ tái lập tập đã
công bố với code/case đã freeze, không được gọi là test độc lập mới. Không
thay code, prompt hay nhãn gold sau kết quả test này.

Access for free at openstax.org. Evidence/chunk theo CC BY-NC-SA 4.0; attribution
và trang nguồn giữ trong trace/review.
