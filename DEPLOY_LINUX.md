# دیپلوی Linux برای carnowash.ir

این پروژه با Docker Compose، MySQL، Django/Gunicorn، Vue/Nginx و edge Nginx برای TLS آماده شده است.

## پیش‌نیازهای سرور

- رکوردهای DNS دامنه‌های `carnowash.ir` و `www.carnowash.ir` باید به IP `185.137.62.158` اشاره کنند.
- پورت‌های `80` و `443` روی firewall سرور باز باشند.
- Docker و Docker Compose Plugin نصب باشند.

## راه‌اندازی اولیه

```bash
cd /path/to/carvash
cp .env.production.example .env.production
nano .env.production
```

در `.env.production` مقدارهای `DJANGO_SECRET_KEY`، `DB_PASSWORD`، `DB_ROOT_PASSWORD` و `LETSENCRYPT_EMAIL` را تنظیم کن. اگر همین فایل آماده را روی سرور داری، فقط مقادیر را بازبینی کن.

سپس اجرا کن:

```bash
chmod +x scripts/deploy_linux.sh scripts/renew_tls_linux.sh
./scripts/deploy_linux.sh
```

این اسکریپت stack را build و اجرا می‌کند، migrationها را داخل بک‌اند انجام می‌دهد، فایل‌های static را جمع می‌کند، داده‌های اولیه production را seed می‌کند، certificate دامنه را از Let's Encrypt می‌گیرد و edge Nginx را روی HTTPS reload می‌کند.

## داده‌های اولیه

در اولین boot بک‌اند، این حساب‌ها ساخته یا sync می‌شوند:

- پنل HQ: نام کاربری `miladdhs`
- کارواش یک: نام کاربری `manager1`
- کارواش دو: نام کاربری `manager2`

برای هر کارواش، خدمات پایه، دسته‌بندی محصولات، محصولات نمونه، موجودی اولیه و تنظیمات عمومی هم ساخته می‌شود.

## دستورهای عملیاتی

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml ps
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml logs -f backend
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml logs -f edge-nginx
```

اجرای دستی migration و seed:

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml exec backend python manage.py migrate
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml exec backend python manage.py seed_production_data
```

تمدید دستی TLS:

```bash
./scripts/renew_tls_linux.sh
```

## آدرس‌ها

- سایت: `https://carnowash.ir`
- Health API: `https://carnowash.ir/api/health/`
