# Path: docs/architecture_and_workflow.md

# Kiến Trúc Hệ Thống & Quy Trình Làm Việc (Anki-Vibe)

Tài liệu này mô tả triết lý thiết kế, cấu trúc dữ liệu và quy trình đồng bộ hóa cho dự án `anki-vibe`.

## 1. Triết Lý Cốt Lõi (Core Philosophy)

* **Code-as-Source-of-Truth:** Mã nguồn là nguồn dữ liệu gốc.
* **Primary Direction (Push):** Luồng chính là `Code -> Anki`.
* **Controlled Reverse Sync (Pull):** Hỗ trợ kéo dữ liệu từ Anki về Code (`Anki -> Code`) nhưng phải thực hiện thủ công và có kiểm soát qua Git.
* **Schema-Centric:** Dữ liệu tổ chức theo Note Types.

## 2. Quy Trình Làm Việc (Workflow)

### A. Quy trình Update thông thường (Push)

1. **Edit:** Sửa file YAML/HTML trên Code Editor.
2. **Sync:** Chạy `python src/main.py sync`.
3. **Review:** Học trên Anki.

### B. Quy trình Sửa trên App & Đồng bộ ngược (Pull-on-Demand)

Đây là quy trình an toàn để không bị mất dữ liệu hay hỏng format YAML.

1. **Modify (Anki):** Sửa note trên Anki App (sửa typo, thêm ý...).
2. **Git Commit (Checkpoint):** **BẮT BUỘC** commit code hiện tại để tạo điểm lưu.
    * `git add . && git commit -m "pre-pull save"`
3. **Pull:** Chạy lệnh sync ngược.
    * `python src/main.py pull --profile "UserA"`
    * Tool sẽ dùng `Note ID` để map dữ liệu và dùng `ruamel.yaml` để cập nhật fields mà vẫn giữ nguyên comments.
4. **Review (Git Diff):** Kiểm tra file YAML xem tool đã sửa gì.
    * Nếu ổn: `git commit`.
    * Nếu lỗi: `git reset --hard` để quay lại.

## 3. Cấu Trúc Tổ Chức Dữ Liệu

```text
anki-vibe/
├── data/
│   ├── UserA/
│   │   ├── Basic_English/      # Note Type Name
│   │   │   ├── config.yaml
│   │   │   ├── unit1.yaml
│   │   │   └── ...
```

## 4. Định Dạng Dữ Liệu (YAML)

Sử dụng thư viện `ruamel.yaml` để xử lý.
**Yêu cầu bắt buộc:** Mỗi note phải có `id` (Anki Note ID) để phục vụ việc sync ngược.

```yaml
# data/UserA/Basic_English/unit1.yaml

# ID là bắt buộc để sync ngược.
# Nếu là note mới tạo từ code, tool sẽ tự điền ID sau lần sync đầu tiên.
- id: 169988223344
  deck: "English::Vocabulary"
  tags: ["unit1", "food"]
  fields:
    Word: "Apple"
    # Comment giải thích vẫn được giữ nguyên khi pull
    Meaning: |
      <div>
        <b>Quả táo</b>
      </div>
```

## 5. Module & Thư Viện Chính

* **CLI:** `typer`
* **Validation:** `pydantic`
* **YAML Processing:** `ruamel.yaml` (Round-trip preservation)
* **Anki Connector:** `requests` (AnkiConnect)
