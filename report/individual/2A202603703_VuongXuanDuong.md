# Báo cáo Day 7 — Agentic RAG trên tài liệu Python (Files và Data Science)

- Học viên: **Vương Xuân Dương** · MSSV **2A202603703** · lớp **K5-L3A**
- Ngày thực nghiệm: 14/11/2026
- Repo nộp bài: https://github.com/DaddyDuong/K5-L3A-DAY07-2A202603703-VuongXuanDuong-RetrievalContext
- Repo Day 6 (dữ liệu, embedding, vector store): https://github.com/DaddyDuong/K5-L3A-DAY06-VuongXuanDuong-2A202603703-DataIngestion, commit `77fa9c4`
- Hướng dẫn chạy: [REPRODUCE.md](../../REPRODUCE.md), [RUN_AGENT.md](../../RUN_AGENT.md)
- Phạm vi: phần cơ bản. Không làm thử thách nâng cao.

**Tóm tắt.** Agent dùng model thật (DeepSeek qua OpenRouter) truy xuất trên
vector store Day 6, trả lời tiếng Việt có citation và biết từ chối khi tài liệu
không có thông tin. So sánh 3 phương pháp retrieval (dense, TF-IDF, hybrid RRF)
và 2 cấu hình cải thiện agent trên dev. Không cấu hình nào vượt baseline, nên
giữ baseline. Trên 7 câu test mới, agent tìm đúng evidence 5/5 câu, trả lời
grounded 10/10 điểm, citation hỗ trợ 15/15 và từ chối đúng 2/2 câu thiếu
evidence. Tổng chi phí API là 0,0247 USD.

## 1. Dữ liệu và benchmark

**Nguồn và quyền sử dụng.** Chương 14 (Files) và 15 (Data Science) của
*Introduction to Python Programming*, OpenStax / Rice University, giấy phép
CC BY-NC-SA 4.0. Access for free at openstax.org —
https://openstax.org/details/books/introduction-python-programming. Dùng 52
trang PDF (trang 319–370), trong đó khoảng 42 trang có nội dung. Gold dùng số
trang PDF, thường lớn hơn số trang in trong sách 10 trang. Snapshot PDF, hash
và cách tái tạo nằm trong repo Day 6.

**Index và vector store.** Dùng lại index C của Day 6: 252 chunk, cắt theo
ranh giới đoạn, tối đa 500 ký tự, không overlap. Metadata gồm document ID,
nguồn, trang PDF, trang in, chương, ngôn ngữ và attribution. PostgreSQL 16.16
với pgvector 0.8.7, exact cosine search (không ANN). Day 7 mở database ở chế
độ chỉ đọc, không ingest lại, và kiểm tra fingerprint code/config/corpus cùng
số chiều vector trước khi truy xuất. Không OCR, nên bảng nhiều cột có thể bị
trộn dòng hoặc cắt giữa hai chunk.

**Embedding.** `intfloat/multilingual-e5-small`, revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 chiều, chuẩn hóa L2, chạy
local trên CPU. Prefix `passage: ` cho chunk và `query: ` cho câu hỏi.

**Agent model.** `deepseek/deepseek-v4.1-flash-1017` qua OpenRouter, ghim
endpoint `particle-ai/us/flex`, không tự chuyển sang model khác khi lỗi. Key
nằm ngoài Git. Model chỉ nhận câu hỏi, instruction và context; không bao giờ
nhận gold hay đáp án tham chiếu.

**Benchmark** ([benchmark.json](../../data/benchmark.json), 24 câu):

| Split | Có evidence | Thiếu evidence | Tổng |
|---|---:|---:|---:|
| Dev | 15 | 2 | 17 |
| Test | 5 | 2 | 7 |
| **Tổng** | **20** | **4** | **24** |

- 15 câu dev có evidence lấy từ dev Day 6. Thêm `u01`, `u02` hỏi con số về
  NTFS và benchmark CPU mà sách không có.
- 7 câu test được soạn mới **sau khi** đã chọn cấu hình trên dev, không dùng
  lại 5 câu test của Day 6.
- Câu có evidence ghi nguồn, trang PDF và trích đoạn nguyên văn, có thể kèm
  evidence thay thế. Evidence test được đối chiếu với text layer của PDF trước
  khi chạy retrieval.
- Câu thiếu evidence được xác định bằng audit toàn bộ 52 trang (từ khóa và đọc
  các đoạn liên quan), không dựa vào việc top-k không tìm thấy:
  [dev audit](../../data/dev_absence_audit.json),
  [test audit](../../data/test_absence_audit.json).

**Tiêu chí chấm.**
- Retrieval: một chunk được coi là hit khi đúng nguồn, đúng trang và chứa toàn
  bộ trích đoạn evidence (chính hoặc thay thế) sau khi chuẩn hóa khoảng trắng.
  Gold chỉ dùng để chấm sau khi truy xuất xong.
- Câu trả lời: grounded 0/1/2 theo [BENCHMARK.md](../../BENCHMARK.md)
  (0 = sai hoặc thiếu evidence, 1 = đúng một phần, 2 = đúng và đủ). Chấm bảo
  thủ: câu trả lời đúng ý chính nhưng có chi tiết mà nguồn được dẫn không hỗ
  trợ chỉ được 1.
- Citation: từng citation phải có trong context **và** đoạn được dẫn phải hỗ
  trợ nội dung. Chỉ đúng ID là chưa đủ.
- Câu thiếu evidence: đúng khi agent từ chối và không đoán con số. Citation
  thông tin nền (nếu có) vẫn được chấm riêng.

## 2. Retrieval và thử nghiệm

### Ba phương pháp retrieval

- **Dense:** embedding E5 của câu hỏi, exact cosine trên vector store C.
- **Lexical TF-IDF:** chuẩn hóa NFC và casefold, tách token bằng regex, cosine
  trên vector TF-IDF chuẩn hóa L2, IDF tính trên toàn corpus. Chỉ trả kết quả
  có score dương.
- **Hybrid RRF:** lấy 10 candidate từ mỗi phương pháp, cộng điểm
  `1 / (60 + rank)` với trọng số bằng nhau, hòa điểm thì xét chunk ID. Không
  cộng thẳng cosine với điểm TF-IDF vì hai thang đo khác nhau.

Cả ba chạy trên cùng 252 chunk, cùng câu hỏi gốc tiếng Việt và cùng filter
chương lấy từ nội dung câu hỏi (không lấy từ gold). Filter được áp trước khi
cắt top-k. Kết quả trả về giữ ID, text, score, rank, nguồn, trang và metadata.
Trace hybrid giữ cả rank và score của từng thành phần.

### Bảng kết quả

Các dòng retrieval dùng câu hỏi gốc với một lượt top-3, không gọi LLM. Các
dòng agent dùng query do model tự viết lại, tối đa 3 lượt, nên số liệu hai
nhóm không so sánh trực tiếp với nhau. Ở các dòng agent, Hit@1 và Hit@3 tính
trên lượt search đầu tiên; Context Evidence Rate tính trên context cuối cùng
gửi cho model.

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---:|---:|---:|---|
| Baseline retrieval | Dense, top-3, filter chương nếu câu hỏi nêu, không rerank, 4.000 ký tự | Mốc so sánh | dev | 9/15 (60,0%) | 11/15 (73,3%) | 11/15 (73,3%) | 24,21 ms · 0 USD |
| Phương pháp 2 | TF-IDF, các thiết lập còn lại như trên | Khớp từ khóa chính xác có thể bắt tên hàm, thuật ngữ | dev | 5/15 (33,3%) | 10/15 (66,7%) | 10/15 (66,7%) | 0,52 ms · 0 USD |
| Phương pháp 3 | Hybrid RRF (10 + 10 candidate, k = 60) | Kết hợp ngữ nghĩa và từ khóa | dev | 9/15 (60,0%) | 11/15 (73,3%) | 11/15 (73,3%) | 27,65 ms · 0 USD |
| Agent baseline | Agent + dense, top-3, tối đa 3 search, 4.000 ký tự, giữ chunk theo thứ tự đến | Model tự viết lại query và tìm thêm khi thiếu | dev | 12/15 | 14/15 | 15/15 | 4,52 s/câu · 0,00225 USD |
| Cải thiện 1: English | Như agent baseline, nhưng yêu cầu mọi query viết bằng tiếng Anh | Corpus tiếng Anh nên query tiếng Anh sẽ khớp hơn | dev | 12/15 | 14/15 | 15/15 | 4,02 s/câu · 0,00239 USD |
| Cải thiện 2: Relevance | Như agent baseline, nhưng xếp lại toàn bộ chunk đã tìm theo cosine với câu hỏi gốc rồi mới đóng gói context | Tránh giữ chunk kém liên quan chỉ vì đến trước | dev | 11/15 | 14/15 | 15/15 | 4,07 s/câu · 0,00222 USD |
| Cấu hình đã chọn = Agent baseline | Như agent baseline | Chốt trên dev, khóa trước test | test | 4/5 (80%) | 5/5 (100%) | 5/5 (100%) | 4,16 s/câu · 0,00143 USD |
| Baseline | Cùng cấu hình và cùng 7 trace với dòng trên | — | test | 4/5 | 5/5 | 5/5 | như trên |

Thời gian retrieval là trung vị một lần đo, đã tách riêng thời gian khởi động
và warmup, và xoay thứ tự ba phương pháp theo từng câu. Thời gian agent là
trung vị wall time mỗi câu khi chạy 3 worker song song; vì retrieval bị khóa
tuần tự nên số này gồm cả thời gian chờ. Chi phí retrieval bằng 0 vì chạy
local, chưa tính phần cứng và điện. Chi phí agent là tổng do provider báo cho
17 câu dev hoặc 7 câu test.

Relevance tính embedding câu hỏi gốc một lần mỗi câu và chỉ dùng chunk đã có
trong candidate pool, không dùng gold. English chỉ đổi instruction. Vì baseline
cũng hay tự viết query tiếng Anh, English thực chất so sánh "yêu cầu tiếng Anh
rõ ràng" với "để model tự chọn", không phải tiếng Việt với tiếng Anh.

### Phân tích lỗi trên dev

**Lỗi 1 — q06 (thư viện đọc PDF ở chương 14): dense bỏ sót, hybrid cũng không cứu được.**
Evidence về PyPDF ở trang 331. Dense không có chunk này trong 10 candidate đầu.
TF-IDF xếp nó hạng 2, nhưng RRF vẫn đẩy nó ra khỏi top-3 vì các chunk nhiễu
xuất hiện ở cả hai danh sách được cộng điểm hai lần. Agent xử lý được câu này:
ở cả ba cấu hình, model viết lại query ở lượt search thứ hai và tìm ra trang
331. Đây là lợi ích của việc tìm nhiều lượt, chưa chứng minh riêng instruction
English có tác dụng.

**Lỗi 2 — q10 và q14: hybrid được ở câu này, mất ở câu khác.**
Ở q14 (`df[condition]`), dense xếp chunk đúng hạng 6, còn hybrid đẩy lên hạng 2.
Ở q10 (`np.array()`), dense xếp chunk đúng hạng 3, nhưng chunk này không có
trong top-10 TF-IDF nên RRF đẩy nó ra khỏi top-3. Lợi và hại bù trừ nhau nên
tổng điểm hai bên bằng nhau. Ngoài ra ở q09, TF-IDF trả danh sách rỗng vì câu
hỏi tiếng Việt không có từ nào trùng với corpus tiếng Anh.

**Lỗi ở câu trả lời của agent** (chấm bảo thủ):
- **q03:** cả ba cấu hình đều nói đúng là phải cast sang string, nhưng thêm hàm
  `str()` trong khi chunk được dẫn không nêu tên hàm. Chấm 1/2.
- **q04:** English và Relevance nhắc thêm `writelines()`, nhưng chunk được dẫn
  là một bảng chỉ ghi `file.write([...])`. Chấm 1/2. Baseline không nhắc nên
  được 2/2.
- **u01, u02:** cả ba cấu hình đều từ chối đúng. Tuy vậy, baseline ở u01 dẫn
  một chunk bị cắt trước câu nói về `close()`, còn Relevance ở u02 dẫn đoạn về
  thao tác mảng để nói về lợi ích bộ nhớ. Hai citation nền này bị chấm sai.

**Lý do chọn baseline.** Tiêu chí được ghi trước khi chạy: không có lỗi thực
thi, từ chối đúng cả hai câu thiếu evidence, sau đó ưu tiên lần lượt điểm
grounded, tỷ lệ citation hỗ trợ, context evidence, chi phí và thời gian. Cả ba
cấu hình đều qua hai điều kiện đầu. Baseline cao nhất ở điểm grounded (29/30 so
với 28/30) và citation (29/31 so với 26/28 và 25/28). Hai cải tiến không giúp vì
baseline vốn đã tự viết query tiếng Anh, và budget 4.000 ký tự đủ rộng để cả
ba cấu hình giữ được evidence 15/15, nên rerank context không còn gì để cải
thiện. Với 17 câu và một lần chạy, chênh lệch 1 điểm chưa đủ để kết luận cấu
hình nào tốt hơn một cách tổng quát.
[Chi tiết kết quả và nhãn dev](../../artifacts/agent-dev/README.md) ·
[chi tiết retrieval](../../artifacts/retrieval/README.md).

## 3. Agent và đánh giá

**Tool.** Agent có hai tool:
- `search(query)`: chạy dense retrieval với filter của câu hỏi và trả về chunk
  thật kèm ID và nguồn.
- `finish(answer, citations, abstain)`: kết thúc bằng câu trả lời tiếng Việt,
  danh sách chunk ID được dẫn và cờ `abstain` cho biết agent có từ chối hay không.

**Số lượt gọi và điều kiện dừng.** Agent phải search ít nhất một lần trước khi
được finish, và search tối đa 3 lần. Sau lượt thứ 3, model chỉ còn được gọi
tool `finish` (`tool_choice: required`), tức là bị buộc phải kết thúc. Nếu
model gửi nhiều search một lúc, các lệnh được chạy tuần tự trong giới hạn còn
lại; lệnh vượt giới hạn không chạy và được ghi vào `skipped_tool_calls`.

**Chọn context.** Bỏ chunk trùng lặp, giữ nguyên chunk và nguồn theo thứ tự
truy xuất, dừng khi đầy budget 4.000 ký tự. Budget đo bằng ký tự, không phải
token. Ở mỗi lượt, model chỉ nhận context tích lũy mới nhất cùng danh sách
query đã dùng, không nhận lại các context cũ, để budget không bị nhân lên.
Nội dung tài liệu được coi là dữ liệu, không phải chỉ dẫn cho model.

**Citation và thiếu evidence.** Mỗi citation phải xuất hiện trong câu trả lời
và có trong context. Câu trả lời không có citation hợp lệ sẽ bị chuyển thành
từ chối. Khi model đặt `abstain = true`, kết quả được ghi là từ chối, kể cả khi
có kèm citation thông tin nền. Parser phân biệt cú pháp chỉ số Python (như
`a[0]`) với citation.

**Xử lý lỗi.** Lỗi kết nối hoặc lỗi model trả trạng thái `error` (exit code 1),
không thay bằng câu trả lời giả. Nếu JSON hoặc citation sai định dạng, agent
thử lại tối đa một lần với cùng câu hỏi và context. Không thử lại vì câu trả
lời bị chấm điểm thấp. Mọi response lỗi và chi phí của chúng đều được giữ.

### Đánh giá agent

| Cấu hình / split | Tool use | Số lượt gọi (model / search) | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---:|---:|---|---:|---:|---:|---:|
| Baseline / dev | 17/17 | 38 / 22 | 0/1/14 · 1,933 | 29/31 | 15/15 | 2/2 | 0/15 |
| English / dev | 17/17 | 39 / 21 | 0/2/13 · 1,867 | 26/28 | 15/15 | 2/2 | 0/15 |
| Relevance / dev | 17/17 | 39 / 22 | 0/2/13 · 1,867 | 25/28 | 15/15 | 2/2 | 0/15 |
| Baseline = đã chọn / test | 7/7 | 18 / 13 | 0/0/5 · 2,000 | 15/15 | 5/5 | 2/2 | 0/5 |

"Citation hợp lệ" là số citation vừa có trong context vừa được đoạn nguồn hỗ
trợ nội dung. Không có lỗi thực thi ở run dev cuối và run test. Trên test,
context của cả 5 câu có evidence được chấm 2/2. Có 3 câu chỉ search 1 lượt, 2
câu search 2 lượt và 2 câu search đủ 3 lượt.

### Từng câu test

Các trang trong cột Tool call là trang PDF của 3 chunk trả về ở mỗi lượt search.

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| t01 | Có evidence, gold tr. 323 | 1 search `open() default mode read-only file Python` → tr. 323, 324, 324; hit top-1 | Mặc định chỉ đọc (`r`), không cho sửa; muốn sửa thì mở bằng `w`. 3 citation · 3,94 s · 0,00014150 USD | Grounded 2, context 2, citation 3/3. Trang 323 và 324 hỗ trợ đủ |
| t02 | Có evidence, gold tr. 327 | 1 search về path và tên file → tr. 327, 327, 328; hit top-1 | Cần đường dẫn (path) đi kèm tên file, ví dụ `/users/turtle/desktop/logfile.log`. 3 citation · 4,16 s · 0,00018568 USD | Grounded 2, context 2, citation 3/3. Path, ví dụ và điều kiện cùng thư mục đều có nguồn |
| t03 | Có evidence, gold tr. 329 | 2 search về định dạng CSV → tr. 329, 329, 330 rồi 329 ×3; gold ở top-3 nhưng không ở top-1 | Hàng phân cách bằng `\n`, ô phân cách bằng dấu phẩy. 2 citation · 6,09 s · 0,00017399 USD | Grounded 2, context 2, citation 2/2. Phần nói thêm về `readlines()` có trong đoạn ví dụ |
| t04 | Có evidence, gold tr. 353 | 3 search về `unique()` → tr. 353, 354, 369 / 353, 369, 355 / 353, 359, 353; hit top-1 nhưng vẫn search đủ 3 lượt | Trả về mảng các giá trị không trùng lặp, ví dụ cột `Season`. 2 citation · 10,07 s · 0,00038295 USD | Grounded 2, context 2, citation 2/2. Không tự khẳng định thứ tự sắp xếp khi nguồn không nêu. Hai lượt search thừa làm tăng chi phí |
| t05 | Có evidence, gold tr. 361 | 1 search về bảng các loại biểu đồ → tr. 361, 364, 370; hit top-1 | Scatter plot, vẽ bằng `plt.scatter(x, y)`. 2 citation · 3,54 s · 0,00011696 USD | Grounded 2, context 2, citation 2/2. Khớp bảng các loại biểu đồ |
| tu01 | Thiếu evidence | 2 search về `read_csv` và AES-256 → tr. 350, 350, 368 / 350, 350, 348 | Từ chối: tài liệu chỉ nói `pd.read_csv()` đọc CSV thành DataFrame, không nhắc AES-256. 1 citation nền · 3,80 s · 0,00014701 USD | Từ chối đúng, citation nền 1/1. Audit toàn corpus không có AES hay mã hóa |
| tu02 | Thiếu evidence | 3 search về `dpi` và `savefig` → tr. 363, 368, 366 / 337, 353, 358 / 362, 349, 366 | Từ chối: các đoạn về Matplotlib chỉ hướng dẫn vẽ biểu đồ, không nêu dpi mặc định. 2 citation nền · 8,82 s · 0,00027856 USD | Từ chối đúng, citation nền 2/2. Audit toàn corpus không có dpi hay savefig |

### Trace, lệnh chạy, thời gian và chi phí

- Retrieval dev: [artifacts/retrieval](../../artifacts/retrieval/README.md) —
  45 lượt (3 phương pháp × 15 câu), lệnh `starter/benchmark_retrieval.py`.
- Agent dev: [artifacts/agent-dev](../../artifacts/agent-dev/README.md) — run cuối
  `20261114T085042869723Z` có 51 trace (3 cấu hình × 17 câu) và nhãn theo cấu
  hình. Lệnh `starter/benchmark_agent_dev.py`, tổng hợp bằng `starter/summarize_agent_dev.py`.
- Agent test: [artifacts/agent-test](../../artifacts/agent-test/README.md) — run
  `20261114T090432454098Z` có 7 trace và
  [nhãn từng câu và từng citation](../../artifacts/agent-test/20261114T090432454098Z/baseline/reviews.json).
  Lệnh `starter/benchmark_agent_test.py`, tổng hợp bằng `starter/summarize_agent_test.py`.
- Mỗi trace giữ request gửi model (không có header Authorization), response,
  usage và chi phí do provider báo, tham số tool, chunk kèm score và metadata,
  context sau mỗi lượt, câu trả lời, citation và thời gian.
- Chi phí API do provider báo: 3 run dev 0,02323489 USD (gồm 2 run lỗi bên
  dưới), run test 0,00142665 USD, **tổng 0,02466154 USD**. Chưa tính các lần
  chạy thử ban đầu (usage của chúng vẫn nằm trong trace riêng), CPU, điện và mạng.

### Lịch sử sửa lỗi

Hai run dev đầu tiên được giữ nguyên trong repo. Run 1 có 15/51 câu lỗi, run
2 còn 4/51 câu lỗi. Nguyên nhân: parser nhầm chỉ số Python với citation, JSON
escape sai, và câu từ chối có kèm citation nền bị ghi nhầm thành câu trả lời.
Sau khi sửa code dùng chung cho mọi cấu hình, chạy lại toàn bộ 51 câu (không
chỉ chạy lại các câu lỗi). Run 3 không còn lỗi và là run dùng để chọn cấu hình.

### Kết quả trước và sau, đánh đổi

- **Từ retrieval một lượt sang agent:** Context Evidence Rate trên dev tăng từ
  11/15 (dense một lượt, query gốc) lên 15/15 (agent baseline). Đổi lại, thời
  gian tăng từ khoảng 24 ms lên khoảng 4,5 s mỗi câu, và tốn khoảng 0,00013 USD
  mỗi câu cho API. Phần cải thiện chủ yếu đến từ việc model viết lại query
  sang tiếng Anh và được tìm thêm lượt.
- **Hybrid và dense:** cùng tổng điểm nhưng thành công ở các câu khác nhau, và
  hybrid chậm hơn một chút. Chọn dense vì đơn giản hơn.
- **Search thừa:** ở t04, agent đã có evidence ngay lượt đầu nhưng vẫn search
  đủ 3 lượt, làm chi phí câu đó gấp khoảng 2,6 lần các câu chỉ search một
  lượt. Điều này chỉ được ghi nhận sau test; không sửa điều kiện dừng rồi chạy
  lại test để lấy điểm đẹp hơn.

## 4. Quy trình khóa test và xác nhận nhãn

- [Nhãn dev trước test](../../artifacts/dev_review_before_test.json) là lần
  rà soát nhãn dev thứ hai trước khi chạy test. Lựa chọn cấu hình và code
  agent không đổi.
- [Freeze manifest](../../artifacts/test-freeze.json) lưu SHA-256 của code,
  model/provider, câu hỏi, lựa chọn cấu hình, nhãn dev và snapshot corpus, được
  ghi trước khi chạy test.
- [Test-start marker](../../artifacts/test_started.json) được ghi trước lần gọi
  retrieval hoặc model đầu tiên. Runner kiểm tra hash trước và sau khi chạy, và
  không cho chạy test chính thức thêm lần nữa.
- Unit test `tests/test_submission_integrity.py` kiểm tra mọi file đã freeze
  vẫn khớp hash.

**Dùng AI và xác nhận nhãn.** Codex hỗ trợ viết code, soạn benchmark và chấm
nhãn bằng cách đối chiếu với nguồn. Tôi đã đọc và xác nhận benchmark (câu hỏi,
đáp án, evidence, audit thiếu evidence) cùng toàn bộ nhãn dev và test, không
sửa nhãn nào. Thông tin xác nhận và hash của các file liên quan nằm trong
[student_confirmation.json](../../artifacts/student_confirmation.json). Lần xác
nhận diễn ra **sau** khi chạy test. Lúc chọn cấu hình trên dev, nhãn vẫn là
bản Codex chấm sơ bộ. Vì vậy các file đã freeze vẫn ghi
`student_confirmed: false`, đúng với trạng thái tại thời điểm đó, và không
được sửa để giữ nguyên hash.

## 5. Tái lập và giới hạn

**Tái lập.** Python 3.14.10, PyTorch CPU; danh sách dependency lấy từ Day 6 ở
`starter/requirements-lock-day6.txt`. [REPRODUCE.md](../../REPRODUCE.md) ghi
cách xem lại kết quả mà không cần API hay database (unit test và hai script
tổng hợp, cho ra kết quả giống hệt bản đã lưu), cách dựng database Day 6, cách
nối model và cách chạy lại. Unit test offline kiểm tra giao thức tool calling,
citation, lỗi provider, vòng lặp agent, freeze guard và hash của file nhãn.
Output của model có thể khác nhau giữa các lần chạy vì không cố định được seed
và hành vi provider có thể thay đổi theo thời gian.

**Giới hạn.**
- Test chỉ có 7 câu, cùng corpus và cùng cuốn sách với dev, chạy một lần.
  Đây không phải holdout tách theo tài liệu và không chứng minh khả năng khái
  quát ra ngoài corpus.
- Cùng một AI soạn benchmark và chấm nhãn, nên có thể có thiên lệch. Học viên
  xác nhận nhãn sau test, không chấm mù.
- So khớp evidence theo chuỗi con có thể bỏ sót các cách diễn đạt tương đương.
- Bảng trong PDF bị trích xuất lỗi hoặc cắt giữa chunk. Budget context đo bằng
  ký tự thay vì token.
- Context giữ chunk theo thứ tự đến, và agent có thể search thừa lượt như ở t04.

## 6. Thử thách nâng cao

Không thực hiện (tài liệu 100 trang, xử lý bảng/ảnh/biểu đồ và ngưỡng 90%).
Kết quả test phần cơ bản không được dùng để nhận điểm bonus.
