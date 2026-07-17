# AI Test Case Generator (Ollama Edition)

Công cụ sinh test case tự động bằng AI, chạy **100% cục bộ qua Ollama**
- không cần API key, không cần Internet sau khi đã tải model, không
giới hạn quota. Theo đúng kiến trúc pipeline:

```
Domain
  -> Website Crawler (Playwright)        (crawler.py)
  -> Crawl HTML + DOM
  -> Page Understanding                  (crawler.py)
       - DOM Tree
       - Accessibility Tree
       - JS Events
       - Network Requests
  -> Feature Extraction                  (feature_extractor.py)
  -> LLM (Ollama - model cục bộ)         (llm_service.py)
  -> Infer Requirements                  (requirement_engine.py)
  -> Generate Test Cases                 (testcase_generator.py)
  -> Export: Excel / Jira / TestRail     (exporter.py)
```

## 1. Cài Ollama (chỉ 1 lần)

Tải và cài tại https://ollama.com/download. Sau khi cài, Ollama tự
chạy nền (icon khay hệ thống). Kiểm tra:

```bash
ollama list
```

Tải model để dùng (mặc định project dùng `qwen2.5:7b`, ~4.9GB):

```bash
ollama pull qwen2.5:7b
```

Muốn dùng model khác (nhẹ hơn, nhanh hơn với máy yếu, hoặc chất lượng
cao hơn với máy mạnh) thì `ollama pull <model>` rồi sửa `OLLAMA_MODEL`
trong `.env`. Vài lựa chọn phổ biến: `qwen2.5`, `gemma2`, `llama3.2`,
`mistral`, `phi3`.

## 2. Cài đặt project

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

`.env` mặc định đã trỏ tới `OLLAMA_MODEL=qwen2.5:7b` tại
`http://localhost:11434` - không cần sửa gì nếu đã làm đúng bước 1.

## 3. Chạy

```bash
python app.py
```

Nhập URL website cần phân tích. Chương trình kiểm tra kết nối Ollama
NGAY từ đầu (báo lỗi rõ ràng nếu Ollama chưa chạy hoặc model chưa
pull), sau đó tự chạy hết pipeline và xuất file
`output/AI_TestCase_Report_<timestamp>.xlsx`.

## LLM: Ollama - vì sao nhanh và ổn định

Khác với gọi API cloud (Groq/OpenAI/OpenRouter), module `llm_service.py`
gọi thẳng REST API **gốc** của Ollama (`/api/chat`), tận dụng 3 tính
năng giúp nhanh + ổn định hơn hẳn:

| Tính năng | Lợi ích |
|---|---|
| `format="json"` | Ép Ollama LUÔN trả JSON hợp lệ cú pháp, giảm hẳn lỗi parse do model tự chèn markdown/giải thích |
| `keep_alive` | Giữ model trong RAM/VRAM giữa các lần gọi (mặc định 30 phút) - tránh phải load lại model (5-30s) mỗi lần, rất đáng kể khi pipeline gọi LLM hàng chục lần |
| `options.num_ctx` | Set rõ context window (8192 mặc định) - Ollama mặc định chỉ 2048 token nếu không set, dễ cắt mất dữ liệu input dài |

Vì chạy cục bộ, không bị giới hạn token/phút hay token/ngày như gói
Free của dịch vụ cloud, nên batch size mỗi lần gọi LLM (`LLM_CHUNK_SIZE`,
`TESTCASE_CHUNK_SIZE` trong `.env`) có thể để lớn hơn hẳn, giảm số lần
gọi LLM (ít round-trip hơn = nhanh hơn) mà vẫn ổn định.

Chương trình còn giữ cơ chế cache kết quả LLM trên đĩa (`cache/llm_cache/`):
nếu bị dừng giữa chừng, chạy lại sẽ tự "resume" đúng chỗ, không gọi lại
LLM cho phần đã xong.

### Tinh chỉnh tốc độ / chất lượng qua `.env`

- Máy yếu, muốn chạy nhanh hơn: giảm `OLLAMA_NUM_CTX` (vd `4096`), dùng
  model nhẹ hơn (`OLLAMA_MODEL=llama3.2` hoặc `phi3`).
- Máy mạnh (GPU rời, nhiều RAM), muốn chất lượng cao hơn: tăng
  `OLLAMA_NUM_CTX` (vd `16384`), dùng model lớn hơn.
- Muốn có model dự phòng khi model chính lỗi: khai báo
  `OLLAMA_FALLBACK_MODELS=qwen2.5,gemma2` (đã `ollama pull` sẵn).

## Bám sát website thật (chống LLM tự đoán/bịa)

Bản này đã sửa lại toàn bộ pipeline để test case luôn bám sát dữ liệu
**đã crawl thật** từ website, thay vì để LLM tự suy diễn:

1. **`crawler.py`**: đã bổ sung thu thập `select`/`textarea` thật (trước
   đây bị thiếu hoàn toàn).
2. **`feature_extractor.py`**: mỗi `Requirement` giờ có thêm field
   `elements` - danh sách dữ liệu THÔ (name/id/placeholder/href/text/
   action/url...) lấy trực tiếp từ DOM thật.
3. **`llm_service.py`**: mọi prompt gửi cho LLM giờ có thêm
   `_GROUNDING_RULE` - yêu cầu bắt buộc LLM chỉ được dùng đúng dữ liệu
   trong `elements`.
4. **Excel report**: các sheet có thêm cột "Bằng chứng từ website"
   để người review đối chiếu trực tiếp với trang web.

## Export: Excel / Jira / TestRail

Đặt `EXPORT_TARGET` trong `.env`:

| Giá trị | Kết quả |
|---|---|
| `excel` (mặc định) | File `.xlsx` 3 sheet trong `output/` |
| `json` | Payload JSON trung gian |
| `jira` | Đẩy trực tiếp mỗi test case thành 1 issue trên Jira Cloud |
| `testrail` | Đẩy trực tiếp mỗi test case thành 1 case trên TestRail |