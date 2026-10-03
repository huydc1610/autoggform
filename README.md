# Google Form autofill

Công cụ dòng lệnh dựa trên [googleform-autofill-and-submit](https://github.com/tienthanh214/googleform-autofill-and-submit) (MIT). Công cụ đọc câu hỏi của một Google Form công khai, tạo dữ liệu từ file JSON và gửi phản hồi khi bạn yêu cầu.

## Cài đặt

Yêu cầu Python 3 và thư viện `requests`:

```powershell
python -m pip install -r requirements.txt
Copy-Item config.example.json config.json
```

Sửa `url` trong `config.json` thành URL `viewform` hoặc link rút gọn `https://forms.gle/...` của form cần điền. File `config.json` được Git bỏ qua vì có thể chứa thông tin cá nhân.

## Cấu hình và chạy

1. Xem ID câu hỏi, yêu cầu bắt buộc và các lựa chọn:

   ```powershell
   python main.py --inspect
   ```

   Bạn cũng có thể xem form trước khi tạo `config.json`:

   ```powershell
   python main.py --url "https://docs.google.com/forms/d/e/FORM_ID/viewform" --inspect
   ```

2. Điền câu trả lời vào `answers` bằng đúng ID vừa in ra. Ví dụ:

   ```json
   {
     "url": "https://docs.google.com/forms/d/e/FORM_ID/viewform",
     "answers": {
       "entry.123456789": "Nguyễn Văn A",
       "entry.987654321": "Lựa chọn A",
       "entry.111111111": ["Mục 1", "Mục 2"],
       "emailAddress": "name@example.com"
     }
   }
   ```

   Dùng chuỗi cho câu trả lời ngắn, đoạn văn, một lựa chọn, ngày (`YYYY-MM-DD`) và giờ (`HH:MM`). Dùng mảng chuỗi cho checkbox. Chỉ thêm `emailAddress` nếu `--inspect` hiển thị trường đó. Giá trị của câu hỏi chọn phải trùng chính xác với một lựa chọn được in ra.

3. Kiểm tra dữ liệu sẽ gửi, chưa gửi thật:

   ```powershell
   python main.py
   ```

4. Gửi đúng một phản hồi:

   ```powershell
   python main.py --submit
   ```

## Câu trả lời ngẫu nhiên

Thêm `--random` để tự tạo câu trả lời cho các ID chưa khai báo trong `answers`. Câu trả lời đã cấu hình vẫn được giữ nguyên. Xem trước trước khi gửi:

```powershell
python main.py --random
python main.py --random --submit
```

Lặp lại N lần với một bộ câu trả lời ngẫu nhiên mới ở mỗi lần:

```powershell
python main.py --random --repeat 5           # xem trước 5 bộ, chưa gửi
python main.py --random --repeat 5 --submit  # gửi 5 phản hồi
```

`--repeat` mặc định là `1`, chỉ nhận số nguyên dương và cần dùng cùng `--random` khi lớn hơn `1`. Nếu một lần gửi gặp lỗi, công cụ dừng và không gửi các lần còn lại.

Để loại một lựa chọn khỏi **mọi lần random**, thêm ID câu hỏi và nguyên văn lựa chọn vào `excluded_answers` trong `config.json`:

```json
"excluded_answers": {
  "entry.694225582": ["Dưới 18 tuổi"]
}
```

Xem ID và tên lựa chọn bằng `python main.py --inspect`. Công cụ kiểm tra tên lựa chọn trước khi chạy; nếu một đáp án cố định trong `answers` cũng bị loại, công cụ báo lỗi thay vì gửi. Các lựa chọn còn lại vẫn được lấy ngẫu nhiên ở mỗi lần lặp.

Chế độ này chọn ngẫu nhiên trong các lựa chọn của form; câu checkbox có thể chọn từ một đến tất cả đáp án. Các lựa chọn kiểu "Chưa thực hiện hoạt động nào" hoặc "Tôi không gặp khó khăn đáng kể" được chọn riêng. Với câu không bắt buộc, mỗi lần chạy có 50% khả năng bỏ trống. Công cụ cũng tạo văn bản mẫu, ngày trong 30 ngày gần đây và giờ ngẫu nhiên. Nếu form yêu cầu email mà bạn chưa cấu hình `emailAddress`, công cụ tạo địa chỉ `@example.com` làm dữ liệu mẫu; hãy cấu hình email thật nếu form yêu cầu địa chỉ nhận được thư.

Công cụ kiểm tra các câu bắt buộc trên những trang được đi qua và tự tạo `pageHistory` cho form nhiều trang, kể cả khi câu trả lời chọn nhánh. Không cần nhập `pageHistory` vào JSON. Nếu cần chạy theo lịch, dùng Windows Task Scheduler gọi lệnh `python main.py --submit` sau khi kiểm tra bản xem trước.

## Giới hạn

- Chỉ dùng cho Google Form công khai, không yêu cầu đăng nhập hoặc tải tệp.
- Các lựa chọn "Khác" cần trường phụ riêng, hiện chưa được hỗ trợ.
- Google Forms có thể thay đổi cấu trúc trang; nếu không đọc được câu hỏi, công cụ sẽ dừng trước khi gửi.
- HTTP 200 chỉ xác nhận yêu cầu mạng hoàn tất; hãy kiểm tra mục phản hồi trong Google Forms để xác nhận form đã ghi nhận dữ liệu.

Các script gốc `form.py` và `generator.py` vẫn có thể dùng để xem hoặc tạo mẫu request theo hướng dẫn trong mã nguồn gốc.
