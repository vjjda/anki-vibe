# Kiến Trúc Hệ Thống & Quy Trình Làm Việc (Anki-Vibe)

Tài liệu này mô tả kiến trúc kỹ thuật, luồng dữ liệu và cơ chế đồng bộ hóa của `anki-vibe` (Phiên bản 0.2.0+).

## 1. Mô Hình Hoạt Động (Hybrid Architecture)

Anki Vibe hỗ trợ hai mô hình hoạt động song song, phục vụ các nhu cầu khác nhau:

### A. Mô hình Dự án (Project-based Mode) - *Recommended*

Đây là mô hình phi tập trung, cho phép bạn quản lý từng phần của bộ sưu tập Anki như một dự án phần mềm riêng biệt.

* **Context:** Được xác định bởi file cấu hình `anki-vibe.toml` tại thư mục gốc dự án.
* **Data Scope:** Chỉ quản lý một tập hợp nhỏ các Deck/Model được định nghĩa trong config (thông qua `Query`).
* **State:** Lưu trữ cục bộ tại `.anki_vibe.db` (SQLite) trong thư mục dự án.
* **Use Case:** Tạo bộ thẻ mới, học một ngôn ngữ cụ thể, chia sẻ bộ thẻ trên Github.

### B. Mô hình Monorepo (Legacy Mode)

Đây là mô hình tập trung, quản lý toàn bộ Profile Anki.

* **Context:** Được xác định bằng tham số CLI `--profile ProfileName`.
* **Data Scope:** Quản lý **toàn bộ** Model và Note trong Profile đó.
* **Location:** Dữ liệu được lưu tập trung tại thư mục cài đặt `anki-vibe/data/anki/{ProfileName}`.
* **Use Case:** Backup toàn bộ Anki, chuyển đổi dữ liệu hàng loạt.

## 2. Luồng Dữ Liệu (Sync Logic)

Hệ thống sử dụng cơ chế **State Tracking** để tối ưu hóa hiệu năng và đảm bảo tính toàn vẹn dữ liệu.

### Thành phần chính

1. **YAML Files (Source of Truth):** Nơi người dùng chỉnh sửa.
2. **SQLite DB (State Tracker):** Lưu trữ Hash (SHA-256) của Note và Model tại thời điểm sync gần nhất.
3. **AnkiConnect (Adapter):** Cổng giao tiếp với Anki.

### Quy trình Sync (Push)

1. **Read:** Đọc tất cả file YAML trong project.
2. **Compute Hash:** Tính toán Hash hiện tại của từng Note (dựa trên Fields, Tags, Deck).
3. **Compare:** So sánh Hash hiện tại với Hash trong SQLite DB.
    * *Match:* Bỏ qua (Không thay đổi).
    * *Diff:* Đánh dấu là `Dirty`.
    * *New (No ID):* Đánh dấu là `Create`.
4. **Execute:** Gửi lệnh `multi` (Batch Update) hoặc `addNotes` lên Anki.
5. **Update State:** Nếu thành công, cập nhật Hash mới vào SQLite DB.

### Quy trình Pull

1. **Query:** Gửi Query (từ `anki-vibe.toml`) lên Anki để lấy danh sách Note IDs.
2. **Fetch:** Lấy thông tin chi tiết (Fields, CSS, Templates).
3. **Write:** Ghi đè file YAML/HTML local.
4. **Update State:** Cập nhật ngay lập tức Hash của dữ liệu vừa pull vào SQLite DB (để tránh sync ngược dư thừa).

## 3. Cấu Trúc Dữ Liệu

### A. File Cấu Hình (`anki-vibe.toml`)

Dùng cho Project Mode.

```toml
[project]
name = "JLPT N5"
anki_profile = "User 1"

[[targets]]
name = "Vocab"
model = "Basic"
deck = "Japanese::N5"
query = "deck:Japanese::N5"
folder = "data/vocab"
```

### B. File Dữ Liệu (`notes.yaml`)

```yaml
- id: 169988223344      # Anki Note ID (null nếu là note mới)
  deck: "Japanese::N5"
  tags: ["vocab", "n5"]
  fields:
    Front: "Neko"
    Back: "Con mèo"
```

## 4. Công Nghệ Sử Dụng

* **CLI Framework:** `typer` (Python).
* **Database:** `sqlite3` (Built-in).
* **Config Parsing:** `tomllib` (Python 3.11+).
* **YAML Processing:** `ruamel.yaml` (Preserves comments & layout).
* **Connectivity:** `requests` (HTTP to AnkiConnect).
