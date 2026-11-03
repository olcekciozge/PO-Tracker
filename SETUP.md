# PO Tracker — Accounts V2 ve ortak geliştirme kurulumu

**Kaynak:** Kullanıcının 3 Kasım 2026'da ilettiği `PO-Tracker-main (1).zip`.
`courses`, `grades` ve `outcomes` modüllerinin Python kodu, README ve requirements dosyası
orijinal haliyle korunmuştur. `.gitignore` içine yalnızca `staticfiles/` eklendi.
`accounts` modülü, daha önce demo ortamında 120 testten başarıyla geçmiş V2 sürümüdür.
Bu birleşik projede 120 testin yeniden geçtiği henüz doğrulanmadı.

## Hızlı başlatma — Windows PowerShell

ZIP'i ayrı bir klasöre çıkarıp o klasörde VS Code terminali aç.
**Her komutu ayrı satırda çalıştır:**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations courses outcomes grades
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test accounts grades
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Tarayıcı: `http://127.0.0.1:8000/accounts/` veya `/admin/`.
İlk `makemigrations` komutu, arkadaşların migration yazmadığı için gereklidir;
üretilen `courses/migrations`, `outcomes/migrations`, `grades/migrations`
dosyalarını **Git'e eklemeden önce inceleyin**. Yeni DB kurmadan önce
paylaşımlı veritabanında migration uygulanıp uygulanmadığı öğrenilmelidir.

> Yerel veritabanı SQLite'dır. `db.sqlite3` Git'e gönderilmez. Gerçek e-posta gönderimi
> kapalıdır; şifre sıfırlama mesajları terminalde görünür.

## PostgreSQL seçeneği

Geliştirme için SQLite yeterli. Ortak PostgreSQL kullanırken PowerShell'de:

```powershell
$env:PO_TRACKER_DB = "postgres"
$env:POSTGRES_DB = "po_tracker"
$env:POSTGRES_USER = "postgres"
$env:POSTGRES_PASSWORD = "YOUR_LOCAL_PASSWORD"
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5432"
```

Bu değerleri şifreyle birlikte Git'e commit etmeyin. Dışarı açılan sistemde
`DJANGO_DEBUG=0`, güçlü `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` ve uygun e-posta
servisi ayrıca yapılandırılmalıdır.

## Hesapların diğer uygulamalarla bağlantısı

- `accounts.User`: Admin, Bölüm Başkanı (`head`), Eğitmen, Öğrenci.
- `courses.Course.instructor`: `settings.AUTH_USER_MODEL` kullanır.
- `courses.Enrollment.student`: `settings.AUTH_USER_MODEL` kullanır.
- `grades.Grade.student`: `settings.AUTH_USER_MODEL` kullanır.
- `outcomes`: PO, LO ve ağırlık modellerini barındırır.
- Dashboard, ders/not görüntüleme endpointleri ve veri girişi ekranları **henüz yok**.
  Accounts rol koruması bu gelecekteki endpointleri kendiliğinden güvenli yapmaz;
  öğrenci/not/ders sorguları ayrıca nesne bazlı filtrelenmelidir.

## Direct main push — mevcut klona güvenli ekleme

Mevcut Git klonu `D:\Works\PO\PO-Tracker` ise;
ZIP içeriğini önce `D:\Works\PO\_integration_source` gibi **ayrı** bir klasöre çıkart.
**Mevcut klondaki ekip dosyalarını ZIP'tekilerle topluca değiştirme.**

```powershell
cd D:\Works\PO\PO-Tracker
git switch main
git status --short
git pull --ff-only origin main
```

`git status --short` boş olmalı; değilse değişiklikleri kaybetmemek için dur.

Yeni ZIP'ten yalnızca `accounts/`, `config/`, `manage.py` ve `SETUP.md`
dosyalarını Git klonuna kopyala. `accounts` veya `config` zaten bulunuyorsa
üzerine yazmadan farkları kontrol et. Ardından Django komutlarını
**bu Git klonunda** çalıştır ve oluşturulan migration'ları da dahil et.

```powershell
git status --short
git add accounts/ config/ manage.py SETUP.md INTEGRATION_REPORT.json courses/migrations/ outcomes/migrations/ grades/migrations/
git diff --cached --stat
git diff --cached --check
git commit -m "feat: integrate accounts and local Django configuration"
git pull --rebase origin main
git push origin main
```

Not: `git pull --rebase` yerel commitler ve başkalarının değişiklikleri arasında
çatışma çıkarırsa zorla pushlama; önce çakışmayı çöz.

## Sınırlar

Bu ZIP, kullanıcı modeli, hesap arayüzleri ve orijinal ders/not/çıktı modellerini
birleştirir. Ancak henüz `courses`/`grades`/`outcomes` için UI, endpoint veya
PO hesaplamanın veritabanına uçtan uca bağlanması yoktur. Bu işleri tamamlandı
sayma. Ayrıca 120 accounts testi önceki Windows demoda başarılı olsa da bu ortamda
Django olmadığı için birleşik projede tekrar çalıştırılıp sonuçlar görülmelidir.
