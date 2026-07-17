# AI Test Case Generator (Ollama Edition)

Công cụ sinh test case tự động bằng AI, chạy **100% cục bộ qua Ollama** - không cần API key, không cần Internet sau khi tải model, không giới hạn quota.

## Kiến trúc Pipeline

```
Domain
  ↓
[1-2] Website Crawler (Playwright)
  └─ Crawl HTML + DOM
  └─ Page Understanding (DOM Tree, Accessibility Tree, JS Events, Network)
  ↓
[3] Feature Extraction
  └─ Chuyển dữ liệu thô thành danh sách Feature chuẩn hoá
  ↓
[4] LLM - Website Type Detection
  └─ Phân loại loại hình website
  ↓
[5] Requirement Inference
  └─ Chuẩn hoá yêu cầu nghiệp vụ
  ↓
[5.5] Use Case Synthesis
  └─ Gom yêu cầu thành Use Case ở mức nghiệp vụ
  ↓
[6] Test Case Generation
  └─ Sinh 7+ loại test case
  ↓
[7] Export
  └─ Excel / JSON / Jira / TestRail
```

## Cài đặt

### 1. Cài Ollama

Tải tại https://ollama.com/download

Kiểm tra:
```bash
ollama list
```

Tải model:
```bash
ollama pull qwen2.5:7b
```

### 2. Cài đặt Project

```bash
python -m venv .venv
source .venv/bin/activate  # hoặc .venv\\Scripts\\activate trên Windows

pip install -r requirements.txt
playwright install chromium
```

### 3. Chạy

```bash
python app.py
```

Nhập URL website cần phân tích.

## Các Tính Năng Chính

### 🎯 Bám sát Dữ liệu Thật
- Mỗi Requirement có field `elements` chứa dữ liệu crawl thật
- Mỗi Test Case có field `element_ref` để truy vết
- Grounding rule yêu cầu LLM chỉ dùng dữ liệu có sẵn

### ⚡ Tối ưu Tốc độ
- `format="json"` ép Ollama trả JSON hợp lệ
- `keep_alive` giữ model trong RAM/VRAM
- Cache kết quả LLM trên đĩa

### 🔧 Export Linh Hoạt
- **Excel**: 3 sheet chuyên sâu
- **JSON**: Payload trung gian
- **Jira Cloud**: Đẩy trực tiếp
- **TestRail**: Đẩy trực tiếp

## Troubleshooting

### "Không kết nối được tới Ollama"
- Kiểm tra `ollama serve` đang chạy
- Kiểm tra `OLLAMA_BASE_URL` trong `.env`

### "Model not found"
- Chạy `ollama pull qwen2.5:7b`
- Hoặc đổi `OLLAMA_MODEL` trong `.env`

## License

MIT
