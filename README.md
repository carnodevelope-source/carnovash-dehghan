# CarWash Management Platform

Production-ready monorepo for a carwash platform with:

- `frontend/`: Vue 3 app served by Nginx
- `backend/`: Django + DRF API served by Gunicorn
- `ai/`: plate-recognition microservice
- `db`: MySQL 8.4 with persistent volume

## Production Docker Stack

The default `docker-compose.yml` is now the production stack:

- `frontend` is the public entrypoint on port `80`
- `frontend` proxies `/api/*` to `backend`
- `backend` runs migrations and collectstatic on boot
- `plate-ai` is a private internal service used by the backend
- `db` stores MySQL data in a named Docker volume

Prepare Docker env values:

```powershell
Copy-Item .env.docker.example .env.docker
```

Start the stack:

```powershell
docker compose --env-file .env.docker up -d --build
```

For a GPU server, use the GPU override too:

```powershell
docker compose --env-file .env.docker -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Useful checks:

```powershell
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs -f backend
docker compose --env-file .env.docker logs -f plate-ai
```

Public endpoints after boot:

- `http://SERVER_IP/`
- `http://SERVER_IP/api/health/`

## Local Non-Docker Dev

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
python manage.py runserver 0.0.0.0:8000
```
