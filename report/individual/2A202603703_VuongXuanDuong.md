# Day 7 — Agentic RAG: Python Files và Data Science

- Học viên: **Vương Xuân Dương** · MSSV **2A202603703** · lớp **K5-L3A**.
- Ngày thực nghiệm: 14/11/2026.
- Hướng dẫn chạy: [REPRODUCE.md](../../REPRODUCE.md), [RUN_AGENT.md](../../RUN_AGENT.md).
- Repo nộp bài: https://github.com/DaddyDuong/K5-L3A-DAY07-2A202603703-VuongXuanDuong-RetrievalContext
- Trạng thái: hoàn thành phần cơ bản; không làm thử thách nâng cao.
- AI hỗ trợ lập trình, tạo benchmark và đọc đối chiếu nguồn: Codex. **Tất cả
  nhãn định tính trong Day 7 là Codex draft, chưa được học viên xác nhận.**

## 1. Dữ liệu, index và benchmark

Dùng lại corpus Day 6: chương 14 Files và chương 15 Data Science của OpenStax /
Rice University, *Introduction to Python Programming*. Giữ 52 trang PDF vật lý
319–370, đếm bảo thủ 42 trang nội dung. Metadata giữ document ID, nguồn, trang
PDF, trang in, chapter, language và attribution. Không OCR; bảng nhiều cột có
thể bị đan xen hoặc cắt giữa chunk. Dùng page PDF làm gold, không nhầm với
page in trong sách (thường chênh 10 trang).

**Access for free at openstax.org.** PDF/chunk/evidence theo CC BY-NC-SA 4.0.
Nguồn: https://openstax.org/details/books/introduction-python-programming .
Snapshot/hash và cách tái tạo giữ ở repo Day 6; trace có source URL và attribution.

Index được dùng là C, 252 chunk ưu tiên ranh giới đoạn, tối đa 500 ký tự,
không overlap. PostgreSQL 16.16 + pgvector 0.8.7, cosine exact search; không
ANN. Embedding `intfloat/multilingual-e5-small`, revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`, CPU, 384 chiều, L2 normalized,
prefix `passage: ` cho document và `query: ` cho query. Không đổi embedding hay
ingest lại Day 6 trong Day 7. Kết nối đặt read-only; kiểm tra fingerprint và
số chiều trước truy xuất. Corpus/index A/B chỉ được kiểm kê, không dùng để
so sánh ba phương pháp Day 7.

Model agent: `deepseek/deepseek-v4.1-flash-1017` qua OpenRouter, pin endpoint
`particle-ai/us/flex`, không tự fallback. Dùng cấu hình/key ngoài Git; API chỉ
nhận question, instruction và context, không nhận gold hoặc đáp án tham chiếu.

| Split | Có đáp án | Thiếu evidence | Tổng |
|---|---:|---:|---:|
| Dev | 15 | 2 | 17 |
| Test mới | 5 | 2 | 7 |
| Tổng | 20 | 4 | 24 |

[benchmark.json](../../data/benchmark.json) ghép hai split. Dev 15 câu kế thừa
Day 6; thêm u01/u02 yêu cầu con số NTFS hoặc benchmark CPU không có trong
nguồn. Test tạo 7 câu mới sau khi chọn cấu hình dev, không dùng lại 5 câu test
Day 6. Câu có đáp án có nguồn, trang và trích đoạn; evidence test được đối
chiếu trực tiếp text layer PDF trước retrieval. Câu thiếu evidence có audit
toàn 52 trang và đọc các phần liên quan, không dựa vào top-k rỗng.

Test chưa dùng chỉnh hệ thống nhưng cùng corpus/sách với dev, có tổng kết lặp
nội dung và cùng AI tham gia soạn/review. Không phải holdout tách tài liệu,
đánh giá mù hoặc bằng chứng khái quát hóa ngoài corpus. Giới hạn này vẫn đúng
khi điểm trên 7 câu cao.

## 2. Ba phương pháp retrieval

- **Dense:** query embedding E5 và exact cosine trên vector store C của Day 6.
- **Lexical:** TF-IDF L2 cosine, NFC/casefold và tách token bằng word regex.
  IDF tính trên toàn corpus; chỉ trả kết quả score dương.
- **Hybrid:** lấy 10 candidate mỗi phương pháp, hợp nhất bằng RRF
  `sum(1/(60+rank))`, trọng số bằng nhau; tie-break bằng ID. Không cộng trực
  tiếp cosine và TF-IDF score. Trace giữ cả component rank/score.

Cả ba dùng cùng 252 chunk, câu hỏi gốc tiếng Việt và filter chapter do người
dùng nêu trong câu hỏi. Filter áp trước cutoff; không suy filter từ gold.
Kết quả giữ ID/text/score/source/page/metadata. Thay top-k không được tính là
phương pháp mới.

| Phương pháp, dev query gốc | Hit@1 | Evidence Hit@3 | Context evidence | Median retrieval |
|---|---:|---:|---:|---:|
| Dense | 9/15 (60,0%) | 11/15 (73,3%) | 11/15 (73,3%) | 24,21 ms |
| TF-IDF | 5/15 (33,3%) | 10/15 (66,7%) | 10/15 (66,7%) | 0,52 ms |
| Hybrid RRF | 9/15 (60,0%) | 11/15 (73,3%) | 11/15 (73,3%) | 27,65 ms |

Đây là 45 lượt retrieval, không gọi LLM; context chỉ từ top-3 một lượt và
budget 4.000 ký tự. Chi phí API 0 USD, chưa tính phần cứng/điện. Setup/warmup
ghi riêng, xoay thứ tự phương pháp theo câu; timing một lần đo còn nhiễu.
[Config, trace và phân tích](../../artifacts/retrieval/README.md).

Dense hòa hybrid về tổng hit và nhanh hơn trong lần đo nên được chọn tạm.
Hybrid có ích ở q14 (gold dense hạng 6 → hybrid hạng 2) nhưng làm mất evidence
top-3 ở q10 (gold dense hạng 3, vắng trong lexical top-10). q06 có gold lexical
hạng 2 nhưng fusion ưu tiên các chunk nhiễu xuất hiện trong cả hai danh sách.
Không kết luận hybrid luôn tốt hơn dense.

## 3. Agent, context và hai thử nghiệm cải thiện

Agent dùng tool `search` và `finish`. Model tự tạo query, có thể viết lại sang
tiếng Anh hoặc tìm tiếp khi thiếu bằng chứng. Mỗi search trả chunk thật;
`finish` khai báo answer, citations và boolean abstain. Từ chối có citation cho
thông tin nền vẫn mang status abstain. Lỗi kết nối/đầu ra không hợp lệ được
ghi riêng, không giả đáp án. JSON/citation format sai được retry tối đa một
lần; không retry vì điểm chất lượng thấp. Mọi response/chi phí được giữ.

Cấu hình chung: dense C, top-3, tối đa 3 search, budget 4.000 **ký tự**, giữ
nguyên chunk và nguồn. Model có thể trả một batch search; thực thi tuần tự
trong budget, lệnh dư được ghi skipped. Chỉ gửi context tích lũy mới nhất cho
lượt model sau, tránh nhân budget bằng context cũ. Nội dung tài liệu được coi
là dữ liệu, không phải chỉ dẫn. Kiểm tra ID không thay cho kiểm chứng nội dung.

| Cấu hình | Giả thuyết/thay đổi | Query policy | Context policy |
|---|---|---|---|
| Baseline | Agent hiện có | Model tự chọn | Dedup, giữ chunk theo thứ tự đến nếu vừa budget |
| English | Yêu cầu rõ query tiếng Anh có thể giúp corpus tiếng Anh | Mọi query được yêu cầu viết tiếng Anh | Như baseline |
| Relevance | Xếp lại pool có thể tránh giữ evidence kém do đến trước | Như baseline | Cosine giữa câu hỏi gốc và vector chunk đã retrieval, rồi pack lại |

Relevance tạo embedding câu hỏi gốc một lần/case, không dùng gold và không
thêm chunk ngoài candidate pool. English chỉ thay instruction; baseline cũng
có thể tự dùng tiếng Anh, nên không gọi đây là phép so sánh thuần Việt–Anh.

| Agent / dev | Hit@1 lượt đầu | Hit@3 lượt đầu | Context cuối | Grounded tổng /30 | Citation support | Từ chối đúng |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 12/15 | 14/15 | 15/15 | 29/30 | 29/31 | 2/2 |
| English | 12/15 | 14/15 | 15/15 | 28/30 | 26/28 | 2/2 |
| Relevance | 11/15 | 14/15 | 15/15 | 28/30 | 25/28 | 2/2 |

Không trộn bảng agent (query model viết lại, nhiều lượt) với bảng retrieval
query gốc. Context rate có thể cao hơn Hit@3 của lượt đầu. Tool use 17/17 ở cả
ba; từ chối nhầm 0/15. Nhãn grounded 0/1/2: baseline 0/1/14, English 0/2/13,
relevance 0/2/13; trung bình lần lượt 1,933/2, 1,867/2 và 1,867/2. Câu trả lời
có citation 15/15 ở mỗi cấu hình. Model/search calls lần lượt 38/22, 39/21,
39/22. Median wall time 4,52 s, 4,02 s, 4,07 s; API USD 0,00225033,
0,00238724, 0,00221805. Chạy 3 worker, retrieval được khóa tuần tự; latency gồm
chờ khóa, không dùng làm benchmark phần cứng.

| Cấu hình / split | Tool use | Số lượt gọi (model / search) | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---:|---:|---|---:|---:|---:|---:|
| Baseline / dev | 17/17 | 38 / 22 | 0/1/14 · 1,933 | 29/31 | 15/15 | 2/2 | 0/15 |
| English / dev | 17/17 | 39 / 21 | 0/2/13 · 1,867 | 26/28 | 15/15 | 2/2 | 0/15 |
| Relevance / dev | 17/17 | 39 / 22 | 0/2/13 · 1,867 | 25/28 | 15/15 | 2/2 | 0/15 |
| Baseline = selected / test | 7/7 | 18 / 13 | 0/0/5 · 2,000 | 15/15 | 5/5 | 2/2 | 0/5 |

**Giữ baseline theo tiêu chí đã công bố trước:** không lỗi và từ chối đúng
hai câu thiếu evidence, rồi ưu tiên grounded-answer, citation support,
context evidence, chi phí và latency. Hai cấu hình thử nghiệm không cải thiện
trên tập nhỏ này; budget đủ rộng nên cả ba đã giữ được evidence 15/15.
Lựa chọn dùng nhãn Codex sơ bộ, không giả là học viên đã xác nhận.
[Kết quả, nhãn và selection](../../artifacts/agent-dev/README.md).

## 4. Phân tích lỗi và tính minh bạch

- **q06:** dense query gốc không hit top-3. Agent cuối dùng 2 search, đổi query
  và tìm đúng PyPDF trang 331 ở cả ba cấu hình. Chứng minh lợi ích pipeline
  nhiều lượt trên ví dụ này, chưa tách riêng lợi ích instruction English.
- **q03:** câu trả lời chính cast sang string đúng nhưng thêm `str()` không
  được nêu trong chunk dẫn. Chấm bảo thủ 1/2 cho cả ba, công khai lý do để
  học viên xem lại tiêu chí. Không coi kiến thức đúng ngoài nguồn là tự động
  được citation hỗ trợ.
- **q04:** English/relevance nói thêm writelines nhưng chunk bảng hiển thị
  file.write([...]), không xác định rõ tên phương thức. Chấm bảo thủ 1/2,
  ghi khả năng nhầm tên trong sách, không âm thầm sửa nguồn.
- **u01/u02:** baseline/u01 dẫn chunk bị cắt trước câu về close;
  relevance/u02 dẫn đoạn thao tác mảng cho lợi ích bộ nhớ. Vẫn từ chối đúng
  con số không có, nhưng citation nền tương ứng bị chấm false.

Hai run phát triển đầu được giữ: 51 case/15 lỗi, rồi 51 case/4 lỗi. Phát hiện
parser nhầm Python indexing với citation, JSON lỗi escape và trạng thái từ
chối bị nhầm khi có citation nền. Sửa chung rồi chạy lại toàn bộ 51 case,
không thay chọn lọc câu tốt. Run cuối không lỗi. Chi phí ba run dev là
0,02323489 USD, gồm cả run lỗi; không chỉ báo chi phí run tốt.

## 5. Khóa cấu hình và đánh giá test mới

[Dev review trước test](../../artifacts/dev_review_before_test.json) giữ nhãn
và lựa chọn cũ. [Freeze manifest](../../artifacts/test-freeze.json) khóa code,
model/provider, cases, selection, review và corpus hash trước test;
[test-start marker](../../artifacts/test_started.json) được ghi trước lần gọi
model/retrieval đầu tiên. Kiểm tra trước/sau cho thấy không thay đổi. Không
chỉnh code, prompt, gold hay cấu hình từ kết quả test.

Baseline chính là selected nên dùng chung một run 7 câu và cùng trace; không
nhân đôi mẫu số hoặc báo thành hai thí nghiệm độc lập.

| Baseline = selected / test | Kết quả |
|---|---|
| Hit@1 lượt đầu | 4/5 (80%) |
| Evidence Hit@3 lượt đầu | 5/5 (100%) |
| Context Evidence Rate | 5/5 (100%) |
| Context grade 0/1/2 | 0/0/5; có lý do từng câu |
| Grounded answer 0/1/2 | 0/0/5; tổng 10/10, trung bình 2,0/2 |
| Citation hỗ trợ | 15/15 (100%) |
| Câu trả lời có citation | 5/5 (100%) |
| Abstention đúng | 2/2 (100%) |
| Từ chối nhầm | 0/5 (0%) |
| Tool use | 7/7 (100%) |
| Lỗi thực thi | 0/7 |
| Model / retrieval calls | 18 / 13 |
| Search distribution | 1 lượt: 3 câu; 2 lượt: 2 câu; 3 lượt: 2 câu |
| Median wall time | 4,16 s/case |
| API provider báo | 0,00142665 USD |

Đã đọc cả 5 câu có đáp án và 2 câu thiếu evidence, với source excerpt và lý
do cho từng citation tại [test review](../../artifacts/agent-test/20261114T090432454098Z/baseline/reviews.json).
Tất cả nhãn nội dung trong bảng là Codex draft.

Chi tiết từng câu test (dense C, top-3; trang là trang PDF của 3 chunk trả về;
thời gian là wall time/case, chi phí do provider báo):

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| t01 | Có đáp án, gold tr. 323 | 1 search `open() default mode read-only file Python` → tr. 323, 324, 324; hit top-1 | Mặc định chỉ đọc (`r`), không cho sửa; muốn sửa mở `w`. 3 citation · 3,94 s · 0,00014150 USD | Grounded 2, context 2, citation 3/3. Đủ default read-only và không cho thay đổi; tr. 323/324 hỗ trợ |
| t02 | Có đáp án, gold tr. 327 | 1 search về path + filename → tr. 327, 327, 328; hit top-1 | Cần đường dẫn (path) đi kèm tên file, ví dụ `/users/turtle/desktop/logfile.log`. 3 citation · 4,16 s · 0,00018568 USD | Grounded 2, context 2, citation 3/3. Path và ví dụ có nguồn; điều kiện cùng thư mục dẫn đúng đoạn |
| t03 | Có đáp án, gold tr. 329 | 2 search về định dạng CSV → tr. 329, 329, 330 rồi 329 ×3; gold ở top-3, không ở top-1 | Hàng phân cách bằng `\n`, ô bằng dấu phẩy. 2 citation · 6,09 s · 0,00017399 USD | Grounded 2, context 2, citation 2/2. Ý thêm về `readlines()` được đoạn ví dụ hỗ trợ |
| t04 | Có đáp án, gold tr. 353 | 3 search về `unique()` → tr. 353, 354, 369 / 353, 369, 355 / 353, 359, 353; hit top-1 nhưng vẫn tìm đủ 3 lượt | Trả về mảng các giá trị không trùng lặp, ví dụ cột `Season`. 2 citation · 10,07 s · 0,00038295 USD | Grounded 2, context 2, citation 2/2. Không tự khẳng định thứ tự sắp xếp khi thiếu evidence. Tìm dư 2 lượt làm tăng chi phí |
| t05 | Có đáp án, gold tr. 361 | 1 search về bảng loại biểu đồ → tr. 361, 364, 370; hit top-1 | Scatter plot; vẽ bằng `plt.scatter(x, y)`. 2 citation · 3,54 s · 0,00011696 USD | Grounded 2, context 2, citation 2/2. Khớp bảng loại biểu đồ |
| tu01 | Thiếu evidence | 2 search về `read_csv` + AES-256 → tr. 350, 350, 368 / 350, 350, 348 | Từ chối: tài liệu chỉ nói `pd.read_csv()` đọc CSV vào DataFrame, không có AES-256. 1 citation nền · 3,80 s · 0,00014701 USD | Abstention đúng, citation nền 1/1. Audit toàn corpus không có AES/encryption |
| tu02 | Thiếu evidence | 3 search về `dpi`/`savefig` → tr. 363, 368, 366 / 337, 353, 358 / 362, 349, 366 | Từ chối: các đoạn Matplotlib chỉ mô tả vẽ biểu đồ, không nêu dpi mặc định. 2 citation nền · 8,82 s · 0,00027856 USD | Abstention đúng, citation nền 2/2. Audit toàn corpus không có dpi/savefig |

Ví dụ có bằng chứng: t01 nêu default read-only, không cho sửa; nguồn trang
323/324 hỗ trợ. Ví dụ từ chối: tu01 không đoán tham số giải mã AES-256 mà chỉ
dẫn mô tả read_csv tạo DataFrame. t03 không hit ở top-1 nhưng có evidence
top-3. t04 đã có evidence lần đầu vẫn tìm đủ 3 lượt, làm tăng chi phí; ghi
nhận sau test, không sửa điều kiện dừng để chạy lại lấy điểm tốt hơn.

[Toàn bộ kết quả test và giới hạn](../../artifacts/agent-test/README.md).
Tổng chi phí ba run agent dev và run test chính thức: **0,02466154 USD**;
chưa gồm các smoke run trước đó, CPU, điện, mạng hay công sức. Các smoke run
có usage riêng trong trace, không gọi là benchmark. Mọi lỗi cũ được giữ lại.

## 6. Tái lập, giới hạn và bài nộp

Python thực nghiệm 3.14.10; 34 unit/integration-interface tests offline pass,
cùng các run database/model thật nêu trên. [REPRODUCE.md](../../REPRODUCE.md)
ghi repo/commit Day 6, dependencies, setup, cách xem kết quả không gọi API và
cách tái lập. Model có thể không cho output giống byte-for-byte; không khóa
seed, provider hoặc model behavior có thể thay đổi theo thời gian. Không tự
fallback sang model khác để giữ điểm.

Hạn chế: test nhỏ, cùng corpus; đánh giá cùng AI soạn benchmark có thiên lệch;
nhãn chưa được học viên xác nhận; evidence substring có thể bỏ sót diễn đạt
tương đương; bảng trích text có lỗi/ngắt chunk; context budget đo ký tự thay
vì token; context policy giữ chunk đến trước và agent có thể tìm dư lượt.
Đây không phải cam kết điểm lab hoặc chất lượng trên tài liệu ngoài corpus.

Không thực hiện bonus tài liệu 100 trang, hình/ảnh/chart extraction và ngưỡng
90% nâng cao. Điểm test cơ bản không được dùng để tuyên bố đạt bonus.

Mã, benchmark, freeze, trace, review và báo cáo nằm trong repo cá nhân
https://github.com/DaddyDuong/K5-L3A-DAY07-2A202603703-VuongXuanDuong-RetrievalContext
(public, fork của repo đề bài; không push vào upstream). Repo Day 6 cũng public.
API key và .env không nằm trong bài nộp.
