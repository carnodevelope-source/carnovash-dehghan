# Commands

دستورهای مهمی که برای دیپلوی، بررسی لاگین، و عیب‌یابی اتصال استفاده کردیم:

## Build / Deploy

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml up -d --build
```

## Service Status

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml ps
```

## Logs

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml logs -f backend
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml logs -f frontend
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml logs -f edge-nginx
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml logs -f plate-ai
```

## Django Ops

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml exec backend python manage.py migrate
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml exec backend python manage.py seed_production_data
```

## HTTP Checks

```bash
curl -I http://carnowash.ir/
curl -I http://carnowash.ir/login
curl -I http://carnowash.ir/api/auth/csrf/
curl -I http://carnowash.ir/api/auth/me/
curl http://127.0.0.1:8765/health
```

## CSRF / Login Checks

```bash
curl -i -c /tmp/cw_cookies.txt http://carnowash.ir/api/auth/csrf/
cat /tmp/cw_cookies.txt
```

برای تست لاگین:

```bash
curl -i -b /tmp/cw_cookies.txt -c /tmp/cw_cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -X POST \
  -d '{"username":"YOUR_USER","password":"YOUR_PASS"}' \
  http://carnowash.ir/api/auth/login/
```

بعد از لاگین:

```bash
curl -i -b /tmp/cw_cookies.txt http://carnowash.ir/api/auth/me/
```

## HTTPS Checks

```bash
curl -Ik https://carnowash.ir/login
curl -Ik https://carnowash.ir/api/auth/csrf/
curl -Ik https://www.carnowash.ir/api/auth/csrf/
```

## TLS / Linux Deploy Scripts

```bash
chmod +x scripts/deploy_linux.sh scripts/renew_tls_linux.sh
./scripts/deploy_linux.sh
./scripts/renew_tls_linux.sh
```
