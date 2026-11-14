# Chạy lại và kiểm tra bài Day 7

Học viên: Vương Xuân Dương — 2A202603703 — K5-L3A.
Kết quả đã có tại [báo cáo](report/individual/2A202603703_VuongXuanDuong.md).
Nhãn nội dung do Codex soạn, học viên đã đọc và xác nhận sau test, không đổi nhãn
([xác nhận](artifacts/student_confirmation.json)).

## Xem kết quả có sẵn, không cần model/API/database

```bash
python3 -m unittest discover -s tests -v
python3 starter/summarize_agent_dev.py artifacts/agent-dev/20261114T085042869723Z
python3 starter/summarize_agent_test.py artifacts/agent-test/20261114T090432454098Z
```

Hai lệnh summarize chỉ tổng hợp nhãn đã chấm, không tự đánh giá nội dung và
không gọi API. Chúng tạo lại cùng summary/selection. Hash selection trong
test freeze vẫn phải khớp; không sửa nhãn rồi ghi đè selection đã dùng test.

## Dựng dữ liệu và database Day 6

Day 7 dùng lại pipeline/embedding/index thật của repo bên cạnh, không tự tạo
vector giả. Repo nguồn:
`https://github.com/DaddyDuong/K5-L3A-DAY06-VuongXuanDuong-2A202603703-DataIngestion.git`,
commit đọc trong workspace khi nộp: `77fa9c4307dd9c069caf05d2fb59ac82c81b84e5`.
Source/config/corpus fingerprint còn được kiểm tra với selection Day 6;
không chỉ dựa vào tên commit. Cần quyền đọc repo hoặc bản snapshot tương ứng.

Đặt hai thư mục cùng cấp theo tên đã dùng. Trên máy mới:

```bash
git clone https://github.com/DaddyDuong/K5-L3A-DAY06-VuongXuanDuong-2A202603703-DataIngestion.git ../K5-L3A-DAY06-VuongXuanDuong-2A202603703-DataIngestion
DAY6_ROOT="$(realpath ../K5-L3A-DAY06-VuongXuanDuong-2A202603703-DataIngestion)"
git -C "$DAY6_ROOT" checkout 77fa9c4307dd9c069caf05d2fb59ac82c81b84e5
```

Các lệnh này dành cho máy chưa có thư mục Day 6. Nếu đã có bài làm, giữ nguyên
và đối chiếu fingerprint, không checkout/ghi đè công việc chưa lưu.

Môi trường đã chạy: Linux x86_64, Python 3.14.10, PyTorch CPU. Lock dependencies
được chép nguyên từ Day 6 tại `starter/requirements-lock-day6.txt`; CPU torch
cần index tương ứng. Từ root Day 7:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install 'torch==2.15.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r starter/requirements-lock-day6.txt
DAY7_PYTHON="$(realpath .venv/bin/python)"
```

Nếu dùng môi trường khác, chọn bản PyTorch phù hợp và ghi rõ thay đổi;
fingerprint benchmark không tự chứng minh môi trường mới cho kết quả giống.
Trên workspace hiện tại có thể dùng venv Day 6:

```bash
DAY7_PYTHON="$DAY6_ROOT/starter/.venv/bin/python"
```

Day 6 cần Docker Compose và Poppler (`pdftotext`, `pdfinfo`). Trong
`$DAY6_ROOT/starter`, tạo `.env` từ `.env.example` nếu chưa có, rồi:

```bash
docker compose -p day6_student_starter up -d --wait
"$DAY7_PYTHON" scripts/check_setup.py
```

Với volume đã có, index C giữ 252 chunk; không ingest lại. Với database mới,
làm theo README Day 6: chuẩn bị PDF/pages, kiểm tra manifest/benchmark rồi
chạy `src.run --split dev --output-root ../results/reproduction` từ starter.
Lệnh đó ingest thật A/B/C. Không chạy test Day 6 để chuẩn bị Day 7. PDF phải
khớp SHA-256 snapshot; URL nguồn có thể đổi, không ghi đè lock để bỏ cảnh báo.

## Nối model

Từ root Day 7, tạo `.env` từ `.env.example`, điền model/key, hoặc trỏ
`--model-env` tới cấu hình được phép dùng. Không commit/copy secret vào report.
Model/provider của lần đánh giá được pin trong freeze manifest. Trên workspace:

```bash
MODEL_ENV="$(realpath ../K5-L3A-DAY04-VuongXuanDuong-2A202603703-ReactLoopAgent/.env)"
"$DAY7_PYTHON" starter/day7_agent.py --dev-id q01 --model-env "$MODEL_ENV"
"$DAY7_PYTHON" starter/benchmark_retrieval.py
"$DAY7_PYTHON" starter/benchmark_agent_dev.py --model-env "$MODEL_ENV"
```

Tài liệu/query/context được gửi tới OpenRouter model; embedding E5 chạy local.
Dev run mới tạo thư mục timestamp riêng, không thay official selection cũ.
Nếu path Day 6 khác, truyền `--day6-root`. README chi tiết adapter tại
[RUN_AGENT.md](RUN_AGENT.md). Model có biến thiên, không cam kết output giống
byte-for-byte. Các lần chạy API có chi phí theo provider thực trả.

## Test đã khóa

`artifacts/test-freeze.json` giữ hash các file code/data/review dùng để đánh
giá. `artifacts/test_started.json` là dấu mốc official test đã bắt đầu;
`test_started:false` trong dev selection là trạng thái lịch sử lúc chốt dev,
không được sửa file frozen đó sau test.

Lệnh official test đã thực hiện:

```bash
"$DAY7_PYTHON" starter/benchmark_agent_test.py --model-env "$MODEL_ENV"
```

Runner sẽ chặn thực hiện official lần nữa. Nếu thật sự muốn tái lập kết quả
đã công bố, dùng:

```bash
"$DAY7_PYTHON" starter/benchmark_agent_test.py --model-env "$MODEL_ENV" --reproduction
```

Reproduction dùng tập đã công bố, không phải test độc lập mới. Phải giữ code,
model/provider, corpus/case và review hash đã freeze. Không xóa marker hay
đổi gold/code để chạy lại lấy điểm cao. Trường hợp cần hệ thống mới, dùng dev
và một test mới, giữ lịch sử kết quả cũ. Nhãn test hiện tại không được dùng
chỉnh hệ thống trong bài đã chốt.

## Hồ sơ cần xem

- `data/benchmark.json`: 24 câu; dev 17, test 7; schema raw Day 6 được giải thích
  trong `data/README.md`.
- `artifacts/retrieval/README.md`: 3 retriever, 45 lượt trên query gốc.
- `artifacts/agent-dev/README.md`: hai thí nghiệm cải thiện, nhãn, run lỗi và chi phí.
- `artifacts/agent-test/README.md`: official test, 7 trace, review, giới hạn.
- `report/individual/2A202603703_VuongXuanDuong.md`: báo cáo cá nhân đã điền.

Access for free at openstax.org. Chunk/evidence theo CC BY-NC-SA 4.0; nguồn,
attribution và page giữ trong artifacts. Code/repo không tự được gán giấy phép
sách. Phần cơ bản được thực hiện; không làm bonus 100 trang.
