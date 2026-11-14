# So sánh ba phương pháp retrieval — dev

Run: [20261114T083953121633Z-dev](20261114T083953121633Z-dev/summary.md).
Xem [config](20261114T083953121633Z-dev/config.json),
[summary JSON](20261114T083953121633Z-dev/summary.json) và
[45 trace](20261114T083953121633Z-dev/traces.json).

| Phương pháp | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Median latency |
|---|---:|---:|---:|---:|
| Dense | 9/15 (60,0%) | 11/15 (73,3%) | 11/15 (73,3%) | 24,21 ms |
| Lexical TF-IDF | 5/15 (33,3%) | 10/15 (66,7%) | 10/15 (66,7%) | 0,52 ms |
| Hybrid RRF | 9/15 (60,0%) | 11/15 (73,3%) | 11/15 (73,3%) | 27,65 ms |

Không có lỗi kết nối trong 45 lượt. Cùng 252 chunk C trong database Day 6,
query gốc tiếng Việt, filter được cung cấp trong câu hỏi, top-3 và budget 4.000
ký tự. RRF dùng 10 candidate mỗi retriever, constant 60 và trọng số bằng nhau.
IDF lexical tính trên cùng toàn corpus, không đưa benchmark vào index.

Theo tiêu chí công bố trước trong config, **dense được chọn tạm trên dev**:
chất lượng tổng thể hòa hybrid và median latency thấp hơn trong lần đo này.
Đây chưa phải lựa chọn agent cuối cùng; timing chỉ một lượt đo, có nhiễu.
Hybrid không cải thiện tổng điểm nhưng thay đổi các câu truy xuất thành công.

## Phân tích lỗi dev

Các nhận xét dưới đây do Codex đối chiếu query, gold và candidate ranking;
học viên đã đọc và xác nhận ([xác nhận](../student_confirmation.json)).

**q06 — thư viện trích xuất thông tin PDF trong chương 14.**
Evidence về PyPDF nằm ở trang PDF 331. Dense không lấy được chunk này trong
10 candidate; TF-IDF xếp chunk đúng ở hạng 2 và đạt Hit@3. RRF vẫn thất bại:
chunk đúng chỉ có đóng góp từ lexical, trong khi những chunk nhiễu được cả hai
retriever tìm thấy nhận điểm cộng từ hai danh sách. Filter chương đã áp dụng
đúng nhưng không đủ để phân biệt đoạn giới thiệu thư viện với đoạn nhắc PDF.

**q10 — hàm chuyển list/tuple thành ndarray.**
Chunk có đầy đủ evidence `np.array()` ở trang PDF 344 đứng hạng 3 của dense,
không có trong top-10 lexical. RRF đẩy chunk đó ra ngoài top-3 vì ưu tiên các
chunk xuất hiện ở cả hai danh sách. Đây là trường hợp hybrid làm mất bằng
chứng mà dense đã tìm được; không thể kết luận hybrid luôn tốt hơn dense.

**q14 — df[condition].**
Theo strict evidence đã khai báo, dense không hit trong top-3 nhưng có chunk
đủ evidence ở hạng 6. Lexical xếp chunk này hạng 3; fusion đưa lên hạng 2 và
đạt Hit@3. Lợi ích này bù một phần mất mát ở các câu khác.

**q09 — hai giai đoạn đầu của vòng đời khoa học dữ liệu.**
Lexical trả danh sách rỗng với query gốc tiếng Việt; dense và hybrid đều hit.
TF-IDF chỉ nhận diện từ chung, không tự ánh xạ diễn đạt tiếng Việt sang thuật
ngữ tiếng Anh. Query rewrite sang tiếng Anh là giả thuyết cải thiện tiếp theo,
chưa được đo trong bảng này.

Các thử nghiệm tiếp theo có thể đo weighted RRF, candidate depth hoặc query
rewrite trên dev. Chưa thực hiện các thay đổi đó, không xem số liệu giả định
là kết quả. Strict evidence match có thể bỏ sót cách diễn đạt tương đương;
chưa thay thế kiểm tra nguồn và chấm chất lượng câu trả lời của agent.

## Kiểm tra agent thật với retriever mới

| Method | Câu | Kết quả | Search calls | Model calls | Chi phí provider báo |
|---|---|---|---:|---:|---:|
| Lexical | q01 | answered, có citation | 2 | 3 | 0,00026978 USD |
| Hybrid | q01 | answered, có citation | 2 | 2 | 0,00019818 USD |

Trace [lexical](../agent/20261114T084015046713Z/trace.json) và
[hybrid](../agent/20261114T084015048355Z/trace.json) giữ nguyên query model thực
sự tạo. Model có viết lại query và tìm nhiều lượt, nên **không trộn hai smoke
run này vào bảng benchmark query gốc**. Citation ID được kiểm tra trong
context; không tuyên bố điểm grounded answer/citation support cho toàn bộ dev.

Chi phí API retrieval trong benchmark bằng 0 USD do chạy local; chưa tính
phần cứng/điện. Chi phí model ở bảng smoke riêng là số do provider trả.
Database Day 6 chỉ đọc, không chỉnh index hay chạy test Day 7.

Các bước tiếp theo đã hoàn thành: [thí nghiệm agent trên dev](../agent-dev/README.md)
và [đánh giá test](../agent-test/README.md).

Access for free at openstax.org. Nội dung chunk theo CC BY-NC-SA 4.0;
nguồn và attribution chi tiết được giữ trong metadata của trace và hồ sơ Day 6.
