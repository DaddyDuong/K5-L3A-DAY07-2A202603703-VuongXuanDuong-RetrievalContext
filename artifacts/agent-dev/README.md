# Thử nghiệm agent/context trên dev

Kết quả chốt: [20261114T085042869723Z](20261114T085042869723Z/summary.md).
Có [summary JSON](20261114T085042869723Z/summary.json),
[selection](20261114T085042869723Z/selection.json),
[config trước khi chạy](20261114T085042869723Z/config.json),
[51 trace](20261114T085042869723Z/traces.json) và review từng cấu hình:
[baseline](20261114T085042869723Z/baseline/reviews.json),
[english](20261114T085042869723Z/english/reviews.json),
[relevance](20261114T085042869723Z/relevance/reviews.json).

**Review do Codex đọc và đối chiếu nguồn. Học viên đã đọc và xác nhận sau khi
chạy test, không đổi nhãn nào ([xác nhận](../student_confirmation.json)). Lúc chọn
cấu hình, nhãn còn là bản Codex sơ bộ; các file đã freeze vẫn ghi
`student_confirmed: false` đúng với thời điểm đó.**

## Điều kiện so sánh

17 câu dev: 15 câu có đáp án từ Day 6, thêm 2 câu hỏi gần chủ đề nhưng thiếu
bằng chứng. [Cases](../../data/dev_cases.json) và
[audit thiếu bằng chứng](../../data/dev_absence_audit.json) có SHA-256 corpus,
danh sách 52 trang và kết quả kiểm tra. Không dựa vào top-k để kết luận thiếu
thông tin. Không thay nhãn Day 6 hay dùng gold làm query/filter.

Cả ba dùng model/provider giống nhau, dense trên 252 chunk C, top-3, tối đa
3 search và 4.000 ký tự context. Baseline giữ ngôn ngữ query do model tự chọn
và context theo thứ tự đến. English chỉ thêm yêu cầu viết query tiếng Anh.
Relevance giữ query như baseline, nhưng xếp lại candidate pool theo cosine
với embedding câu hỏi gốc, không dùng gold và không lấy thêm chunk ngoài pool.

Tiêu chí chọn ghi trước khi chạy: không lỗi, từ chối đúng hai câu thiếu evidence,
rồi ưu tiên grounded-answer, citation support, context evidence, chi phí và
latency. Lỗi JSON/citation format được retry tối đa một lần cho mọi cấu hình;
không retry vì điểm thấp. Giữ nguyên response lỗi và chi phí.

## Kết quả cuối

| Config | Grounded answer | Citation support | Context evidence | Từ chối đúng | API USD |
|---|---:|---:|---:|---:|---:|
| baseline | 29/30 | 29/31 | 15/15 | 2/2 | 0,00225033 |
| english | 28/30 | 26/28 | 15/15 | 2/2 | 0,00238724 |
| relevance | 28/30 | 25/28 | 15/15 | 2/2 | 0,00221805 |

Không có lỗi thực thi cuối cùng; cả ba dùng retrieval tool trên 17/17 câu,
không từ chối nhầm câu có đáp án. Điểm grounded-answer là tổng 15 nhãn 0–2;
chi tiết phân bố và số lượt gọi nằm trong summary JSON. First-search Hit@1/
Hit@3 lần lượt baseline 12/15–14/15, english 12/15–14/15, relevance 11/15–14/15.
Context Evidence Rate dùng toàn bộ evidence chính hoặc alternative, chuẩn hóa
whitespace, trên context cuối thực sự gửi model. Context do Codex đối chiếu
đều đủ nguồn và nội dung cho yêu cầu chính (2/2).

**Chọn baseline trên dev theo nhãn sơ bộ.** Hai cấu hình mới chưa cải thiện:
baseline vốn đã thường tự tạo query tiếng Anh; budget 4.000 ký tự giữ được đủ
evidence ở cả ba cấu hình nên rerank context chưa tăng context evidence rate.
Không suy rộng từ 17 câu/một lượt chạy; model có biến thiên và ngôn ngữ query
có thể giống nhau giữa các cấu hình. Đây không phải so sánh thuần Việt–Anh.

## Lỗi và thay đổi đã đo

**q06 — dense một lượt chưa tìm thấy thư viện PDF.** Benchmark query gốc trước
đó không có evidence trong top-3. Trong lần agent cuối, cả ba cấu hình đều cần
2 search; query lần sau tìm được PyPDF ở trang 331. Context cuối và câu trả lời
của cả ba có evidence. Đây là lợi ích của query transformation/nhiều lượt so
với retrieval một lượt, chưa chứng minh riêng instruction English có lợi.

**q03 — câu trả lời có chi tiết vượt nguồn dẫn.** Cả ba nêu đúng yêu cầu cast
sang chuỗi, nhưng bổ sung cụ thể hàm `str()` trong khi chunk được dẫn chỉ nói
cast sang string. Chấm bảo thủ 1/2 và không chấp nhận citation cho toàn bộ
chi tiết mở rộng này; ghi rõ lý do. Không
coi một hàm đúng kiến thức Python là tự động được nguồn này hỗ trợ.

**q04 — citation không làm rõ tên phương thức mở rộng.** English/relevance
nhắc thêm `writelines()`, dẫn một chunk bảng hiển thị `file.write([...])` và
không nhận diện rõ `writelines`. Dù yêu cầu chính về newline đã trả lời đúng,
chấm bảo thủ 1/2 cho chi tiết thêm; cần đối chiếu khả năng nhầm tên trong sách.
Baseline tránh tên phương thức mở rộng này và được chấm 2/2.

**u01/u02 — từ chối đúng chưa có nghĩa mọi citation nền đều đúng.** Baseline/u01
dẫn chunk bị cắt trước câu nói về `close()`; relevance/u02 dẫn đoạn thao tác
mảng/đại số tuyến tính cho lợi ích bộ nhớ. Cả hai vẫn từ chối con số không có
bằng chứng, nhưng citation tương ứng bị chấm false. Review giữ excerpt nguồn
và lý do cho từng citation, không suy grounding từ ID hợp lệ.

## Lịch sử sửa lỗi chung và chi phí

Giữ đầy đủ hai lần chạy phát triển trước:

- [Run đầu](20261114T084607870102Z/discovery_summary.json): 51 case, 15 lỗi
  parser/protocol; 0,00872178 USD.
- [Run thứ hai](20261114T084904943502Z/discovery_summary.json): 51 case, 4 lỗi
  parser/format còn lại; 0,00765749 USD.
- Run cuối: 51 case, 0 lỗi; 0,00685562 USD.

Tổng API provider báo cho ba lần chạy là **0,02323489 USD**, chưa gồm CPU,
phần cứng/điện. Không gộp các lần chạy lỗi vào bảng so sánh cuối và không giấu
chi phí của chúng. Các sửa lỗi chung trước lần chạy cuối: phân biệt Python
indexing với citation, boolean `finish.abstain`, câu trả lời ngắn với JSON hợp
lệ, và một format-only retry. Chạy lại toàn bộ 51 case sau thay đổi chung,
không chọn lọc câu tốt để thay thế kết quả.

Tại thời điểm chạy dev: 33/33 test offline pass. Các unit test mới kiểm tra thay chunk khi budget đầy,
rerank dùng câu hỏi gốc và deduplicate, instruction English, phân biệt code/
citation, explicit abstention và giới hạn format retry. Database chỉ đọc.

Selection được lưu trước khi tạo/chạy test. Sau bước dev đã hoàn thành
[test trên 7 câu mới](../agent-test/README.md); baseline và selected dùng chung
trace vì cùng cấu hình.

Access for free at openstax.org. Evidence/chunk theo CC BY-NC-SA 4.0; giữ
attribution và nguồn trong trace. Không chứa API key hoặc database URL.
