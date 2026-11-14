# Chạy agent Day 7 với dữ liệu Day 6

Agent dùng model thật qua OpenRouter để chọn query tìm kiếm, đọc context rồi trả
lời tiếng Việt có citation hoặc từ chối khi thiếu bằng chứng. Code tại
`starter/day7_agent.py`, dùng vòng lặp `starter/agentic.py`.

## Môi trường

Chạy các lệnh từ thư mục gốc Day 7. Có thể dùng lại Python và dependencies đã
cài trong môi trường Day 6:

```bash
DAY6_ROOT="$(realpath ../K5-L3A-DAY06-VuongXuanDuong-2A202603703-DataIngestion)"
DAY7_PYTHON="$DAY6_ROOT/starter/.venv/bin/python"
docker compose -f "$DAY6_ROOT/starter/docker-compose.yml" -p day6_student_starter up -d --wait
```

Trên máy khác, dựng môi trường theo `starter/README.md` của Day 6 và dùng đúng
model/revision, corpus, code và cấu hình đã ingest. Dependencies trực tiếp của
adapter được liệt kê tại `starter/requirements-agent.txt`; phiên bản đã kiểm
chứng nằm trong `starter/requirements-lock.txt` của Day 6.

## Cấu hình model

Chép `.env.example` sang `.env` nếu chưa có, điền model hỗ trợ tool calling và
API key OpenRouter. `.env` được gitignore. Có thể dùng cấu hình sẵn có của Day 4
mà không chép secret:

```bash
MODEL_ENV="$(realpath ../K5-L3A-DAY04-VuongXuanDuong-2A202603703-ReactLoopAgent/.env)"
"$DAY7_PYTHON" starter/day7_agent.py --dev-id q01 --model-env "$MODEL_ENV"
```

Nếu đã cấu hình `.env` của Day 7:

```bash
"$DAY7_PYTHON" starter/day7_agent.py --dev-id q01
"$DAY7_PYTHON" starter/day7_agent.py 'Theo chương 14, readline() trả về gì?' --chapter 14
"$DAY7_PYTHON" starter/day7_agent.py --dev-id q01 --method lexical
"$DAY7_PYTHON" starter/day7_agent.py --dev-id q01 --method hybrid --candidates 10 --rrf-constant 60
```

Environment variables ưu tiên hơn file cấu hình. `--model-env` chỉ đọc cấu hình
model; kết nối database lấy từ `DATABASE_URL` hoặc `.env` của Day 6. Query và
context được gửi đến model provider; embedding chạy local. Không tự chuyển
model/provider nếu xảy ra lỗi. Provider được pin bằng `OPENROUTER_PROVIDER` nếu
có cấu hình.

## Hành vi và trace

- Dùng snapshot C của Day 6, exact cosine search, E5 384 chiều với prefix
  `query: ` và chuẩn hóa L2. Kiểm tra fingerprint code/config/corpus/benchmark
  của Day 6 và số chiều cột database trước khi truy xuất.
- Database ở chế độ chỉ đọc; không ingest lại hay thay index Day 6.
- Mặc định tối đa 3 lượt retrieval, top-3, context budget 4.000 **ký tự**.
  Có thể đổi bằng `--max-searches`, `--top-k`, `--budget`. Model có thể viết
  query tiếng Anh cho corpus tiếng Anh; trace lưu cả câu hỏi gốc và query thật.
- Bắt buộc search trước khi finish. Nếu provider trả nhiều search call, thực thi
  tuần tự trong giới hạn lượt tìm. Lệnh dư budget không thực thi, được ghi riêng
  trong `skipped_tool_calls`; context chỉ ghi các query thực sự đã thực thi.
- Deduplicate chunk, giữ nguyên chunk và nguồn theo thứ tự truy xuất nếu còn
  vừa budget. Các lượt sau có thể không thêm được evidence khi budget đã đầy;
  cần đo và cải thiện cách chọn context trên dev.
- Lượt model tiếp theo chỉ nhận context tích lũy mới nhất, danh sách query đã
  tìm và cặp assistant/tool tương ứng; không nhân budget bằng cách nối tất cả
  context cũ. Raw trace vẫn giữ mọi model response và từng lượt search.
- Citation phải xuất hiện trong câu trả lời và context. Đây là kiểm tra ID;
  cần đọc nguồn để xác nhận hỗ trợ nội dung. Không dùng gold để chọn query,
  filter, context hoặc trả lời. `--dev-id` chỉ chuyển question/filter vào agent
  và từ chối ID thuộc test.
- Khi thiếu citation hoặc evidence, vòng lặp trả `abstain`. Lỗi kết nối/model
  trả `error`, exit code 1; không thay lỗi bằng đáp án giả.
- Tool `finish` có boolean `abstain` rõ ràng: từ chối vẫn có thể kèm citation
  cho thông tin nền, nhưng không được ghi nhầm thành answered. Parser phân biệt
  chỉ số Python với citation, kể cả biểu thức không có backtick. JSON/citation
  sai định dạng được thử lại tối đa một lần với cùng question/context; giữ
  response lỗi và chi phí, không retry chỉ vì câu trả lời có điểm thấp.

Mỗi lần chạy tạo `artifacts/agent/<UTC timestamp>/trace.json`, giữ request model
(không có Authorization header), response, usage/cost do provider báo, tool
arguments, chunk/score/metadata, context cuối từng lượt, answer/citations và
timing. Nếu provider không báo cost, giá trị là `null`, không suy đoán bằng 0.
Trace có nội dung tài liệu OpenStax: giữ ghi công và điều kiện CC BY-NC-SA 4.0
theo `data/README.md` của Day 6. Access for free at openstax.org.

## Kiểm tra và phạm vi hoàn thành

```bash
python3 -m unittest discover -s tests -v
```

Test offline kiểm tra protocol tool calling, citation, lỗi provider và vòng
lặp; chất lượng phải đối chiếu trên các lần chạy model thật. Các smoke run
không phải điểm benchmark. Agent hỗ trợ **dense, lexical TF-IDF và hybrid RRF**
trên cùng snapshot C. Hybrid lấy mặc định 10 candidate mỗi retriever, tính
`sum(1 / (60 + rank))`, tie-break bằng chunk ID; không cộng trực tiếp cosine
với TF-IDF score. Trace hybrid giữ component rank/score và danh sách candidate.
Lexical dùng IDF trên toàn corpus; cả ba áp cùng filter trước cutoff kết quả.

## Benchmark ba phương pháp trên dev

```bash
"$DAY7_PYTHON" starter/benchmark_retrieval.py
```

Lệnh đọc 15 câu dev Day 6, giữ nguyên query tiếng Việt, top-3 và budget 4.000
ký tự. Gold chính hoặc evidence thay thế chỉ được dùng để chấm sau retrieval,
khớp nguồn/trang và toàn bộ trích đoạn sau chuẩn hóa whitespace. Không gọi LLM,
không viết lại query và không chạy test. Context Evidence Rate đo context
single-turn, khác với agent có thể gom bằng chứng qua nhiều lượt.

Kết quả từng câu, component ranking, context, fingerprint và tiêu chí chọn được
lưu tại `artifacts/retrieval/<timestamp>-dev/`. Ghi config/tiêu chí trước khi
chạy, xoay thứ tự ba phương pháp theo câu để giảm sai lệch warm-cache; setup
và embedding warmup đo riêng. Chi phí API retrieval là 0 USD vì chạy local,
không tính phần cứng/điện. Chọn tạm theo Hit@3 → Hit@1 → context rate → median
latency; chưa chọn cấu hình agent cuối cùng.

Xem [kết quả retrieval](artifacts/retrieval/README.md),
[thí nghiệm trên 17 câu dev](artifacts/agent-dev/README.md),
[đánh giá test đã khóa](artifacts/agent-test/README.md) và
[báo cáo cá nhân](report/individual/2A202603703_VuongXuanDuong.md).
Các phần này đã được thực hiện local; review nội dung là Codex draft.

Tool calling theo tài liệu chính thức:
https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request

## Hai thử nghiệm cải thiện agent trên 17 câu dev

```bash
"$DAY7_PYTHON" starter/benchmark_agent_dev.py --model-env "$MODEL_ENV"
```

Cùng dense retrieval C, top-3, tối đa 3 search, context 4.000 ký tự:

| Config | Query | Chọn context |
|---|---|---|
| baseline | Model tự chọn ngôn ngữ, như agent hiện có | Theo thứ tự chunk đến, deduplicate |
| english | Yêu cầu model viết mọi search query bằng tiếng Anh | Như baseline |
| relevance | Như baseline | Xếp lại toàn bộ chunk đã tìm bằng cosine với câu hỏi gốc |

`english` thay instruction tạo query, không dịch bằng gold hoặc tự thêm thuật
ngữ từ đáp án. Baseline cũng có thể tự viết query tiếng Anh, nên đây là so sánh
**yêu cầu rõ ràng** với **để model tự chọn**, không phải tiếng Việt với tiếng Anh.
Trace giữ câu hỏi gốc và từng query thật để đối chiếu.

`relevance` tạo embedding câu hỏi gốc một lần/case, lấy cosine từ vector đã
lưu của các chunk có trong candidate pool, sắp lại và pack context sau mỗi
search. Không dùng gold, không thêm chunk chưa retrieval vào context. Context
vẫn giữ nguyên nội dung/nguồn; không cắt mất điều kiện của đoạn.

Runner dùng tối đa 3 worker cho các lời gọi model độc lập; truy xuất database
và embedding được khóa tuần tự. Latency từng case gồm thời gian chờ khóa.
Mỗi case có controller/trace riêng; không chia sẻ context hoặc đáp án giữa câu.

Kết quả lưu ở `artifacts/agent-dev/<timestamp>/`. Sau khi đọc đối chiếu từng
câu trả lời/citation với context và chấm vào `<config>/reviews.json`, tổng hợp:

```bash
python3 starter/summarize_agent_dev.py artifacts/agent-dev/<timestamp>
```

Tiêu chí chọn đã ghi trước khi chạy: không lỗi và từ chối đúng cả hai câu thiếu
bằng chứng; ưu tiên tổng grounded-answer, citation support, context evidence,
chi phí rồi latency. Nhãn do Codex chấm là **sơ bộ**, không ghi thành nhãn người
học đã xác nhận. Selection trên dev không tự kích hoạt chạy test.

## Test mới sau khi khóa cấu hình

`starter/benchmark_agent_test.py` kiểm tra hash theo `artifacts/test-freeze.json`,
chặn official run lần nữa khi `artifacts/test_started.json` đã có. Baseline và
selected cùng cấu hình nên dùng chung trace, không nhân đôi mẫu số. Test đã
hoàn tất; xem [REPRODUCE.md](REPRODUCE.md) để đọc lại kết quả hoặc tái lập tập
đã công bố bằng `--reproduction`. Không gọi reproduction là holdout mới.
