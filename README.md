# Từ điển Xưởng — từ điển offline Trung / Nhật / Hàn ↔ Việt / Anh cho nhà máy

Từ điển **chạy hoàn toàn offline trong một file HTML** (mở bằng Edge/Chrome, không cần cài đặt, không cần internet), dành cho người làm việc trong nhà máy dùng tiếng Trung, tiếng Nhật hoặc tiếng Hàn: đọc thông báo lỗi trên phần mềm máy, tài liệu SOP, trao đổi với đồng nghiệp.

*An offline, single-file HTML dictionary (Chinese / Japanese / Korean ↔ Vietnamese / English) with a ~1,000-term factory glossary (automation, pneumatics, motion control, screw fastening, dispensing, vision, quality, tools, PPE). Just open the .html file in Edge or Chrome.*

## Tải về

Vào mục **[Releases](../../releases)**, tải file phù hợp:

| File | Ngôn ngữ tra | Dung lượng |
|---|---|---|
| `TuDien.html` | Trung ↔ Việt / Anh | ~26 MB |
| `TuDien-Nhat.html` | Nhật ↔ Việt / Anh | ~29 MB |
| `TuDien-Han.html` | Hàn ↔ Việt / Anh | ~23 MB |
| `TuDien-DaNgu.html` | Trung + Nhật + Hàn ↔ Việt / Anh — bật/tắt từng ngôn ngữ bằng nút ⚙ (chỉ giải nén ngôn ngữ được bật) | ~45 MB |
| `…-KhongLoa.html` | Như trên nhưng bỏ nút phát âm 🔊 (máy không có loa) | |

**Chỉ cần chép đúng 1 file .html** sang máy (kể cả máy không có internet) rồi nhấp đúp.

**Phiên bản** có dạng `v1.0.YYMMDD` (số cuối = ngày build), hiện ở góc trên cạnh tên và trong tab Hướng dẫn — so với bản mới nhất ở Releases để biết có cập nhật hay không.

## Tính năng

- **Dán cả câu** (thông báo lỗi, menu phần mềm): tự tách thành từng từ; hiện cách đọc (pinyin / kana / chữ Hán của từ Hàn), **âm Hán-Việt**, nghĩa Việt và Anh.
  - Tiếng Nhật: tự đưa động từ/tính từ đã chia về dạng gốc (開いています → 開く, タイムアウトしました → タイムアウト); nhận trợ từ (の, が, を…).
  - Tiếng Hàn: bỏ tiểu từ và đuôi động từ (흡착 노즐을 → 흡착 노즐, 확인하십시오 → 확인), gộp cụm nhiều từ (원점 복귀).
- **Gõ tiếng Anh hoặc tiếng Việt** (có dấu hay không dấu, vd `bao duong`) → từ tương ứng trong tiếng Trung / Nhật / Hàn, đặt ngay đầu kết quả.
- **Pinyin** không dấu viết liền (vd `dianji`) khi chỉ nghe mà không biết chữ.
- **Bộ thuật ngữ xưởng ~1.250 mục** (khung vàng, luôn hiện trước): phần mềm/HMI, chuyển động–servo, khí nén, cảm biến, an toàn, điện, thị giác máy, chất lượng, SMT, bắt vít, tra keo, MES, bảo trì, dụng cụ cầm tay, dụng cụ đo, vật tư, đồ bảo hộ, từ lập trình, từ vựng phần mềm máy/điều khiển chuyển động (kèm các cách gọi hay gặp trên máy Hàn: 셋팅, 리미트, 홈, 서보팩, 오버라이드…)… Thuật ngữ ghép không có trong từ điển chung vẫn hiện nghĩa từng thành phần.
- **Tự thêm thuật ngữ** của xưởng mình (lưu trong trình duyệt, có xuất/nhập file TSV).
- **Giao diện 5 ngôn ngữ**: Việt, 中文, 日本語, 한국어, English — đồng nghiệp người Trung/Nhật/Hàn dùng được.

## Lưu ý chất lượng

- Nghĩa **tiếng Việt** trong từ điển chung (CVDICT, OVDP Nhật-Việt/Hàn-Việt) phần lớn **dịch bằng máy qua tiếng Anh** → có chỗ sai; khi nghi ngờ hãy xem nghĩa tiếng Anh ngay bên dưới.
- Bản dịch **tiếng Nhật / tiếng Hàn của bộ thuật ngữ xưởng do AI dịch** theo nghĩa nhà máy — **cần người bản ngữ kiểm tra**. Góp ý/sửa: mở issue hoặc pull request vào `data/dich-ja-ko*.tsv`.
- Âm Hán-Việt ghép theo từng chữ, chỉ để tham khảo.

## Tự build

```bash
python build/fetch_sources.py   # tải dữ liệu nguồn vào _src/ (cần internet, ~150 MB)
python build/build.py           # tạo dist/TuDienOffline/*.html (+ từ điển StarDict cho GoldenDict)
```

Cần Python 3.10+ (không cần thư viện ngoài).

| Thư mục / file | Nội dung |
|---|---|
| `VERSION` | Số phiên bản lớn.nhỏ (`1.0`); build tự thêm ngày `.YYMMDD` |
| `data/thuat-ngu-*.tsv` | Bộ thuật ngữ xưởng: `giản thể ⇥ pinyin ⇥ tiếng Việt ⇥ tiếng Anh ⇥ nhóm` (pinyin để trống = tự điền) |
| `data/dich-ja-ko*.tsv` | Bản dịch thuật ngữ sang Nhật / Hàn: `giản thể ⇥ tiếng Nhật ⇥ tiếng Hàn` (nhiều cách gọi ngăn bằng ` / `) |
| `build/build.py` | Gộp từ điển Trung, sinh StarDict cho GoldenDict, đóng gói các bản HTML |
| `build/build_jako.py` | Chuẩn bị dữ liệu Nhật (JMdict + KANJIDIC2 + OVDP) và Hàn (kengdic + OVDP) |
| `build/template.html` | Giao diện + toàn bộ logic tra cứu (một file, không thư viện ngoài) |

### Dùng với GoldenDict (tuỳ chọn)

`build.py` cũng tạo các bộ từ điển StarDict (thuật ngữ xưởng, CVDICT, CC-CEDICT, OVDP) trong `dist/TuDienOffline/GoldenDict/content/`. Tải [GoldenDict-ng](https://github.com/xiaoyifang/goldendict-ng/releases) bản portable, đặt thư mục `content/` cạnh `goldendict.exe` và tạo thư mục `portable/`.

## Nguồn dữ liệu & giấy phép

| Dữ liệu | Tác giả | Giấy phép |
|---|---|---|
| [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) | MDBG & cộng đồng | CC BY-SA 4.0 |
| [CVDICT](https://github.com/ph0ngp/CVDICT) | Phong Phan | CC BY-SA 4.0 |
| [hanviet-pinyin-wordlist](https://github.com/ph0ngp/hanviet-pinyin-wordlist) (Thiều Chửu) | Phong Phan | MIT |
| [JMdict, KANJIDIC2](https://www.edrdg.org/) qua [jmdict-simplified](https://github.com/scriptin/jmdict-simplified) | EDRDG | CC BY-SA 4.0 |
| [kengdic](https://github.com/garfieldnate/kengdic) | Joe Speigle và cộng đồng | MPL 2.0 / LGPL |
| [OVDP](https://sourceforge.net/projects/ovdp/) qua [stardict-vi](https://github.com/dynamotn/stardict-vi) | Open Vietnamese Dictionary Project | GPLv2 |

- **Mã nguồn** (`build/`): MIT — xem `LICENSE`.
- **Bộ thuật ngữ** (`data/`): CC BY-SA 4.0.
- **File HTML phát hành** chứa dữ liệu của các nguồn trên nên tuân theo giấy phép của chúng (CC BY-SA 4.0 / GPLv2 / MPL 2.0): được chia sẻ, chỉnh sửa, kể cả thương mại, miễn là ghi nguồn và chia sẻ cùng giấy phép.
