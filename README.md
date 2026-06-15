# CarWash Management Platform

A modern monorepo skeleton for a comprehensive carwash operations platform.

## Structure
- `frontend/`: Vue 3 + Vite client
- `backend/`: Django + DRF API
- `ai/`: AI/OCR integrations and pipelines
- `Docs/`: Product and system design docs

## Quick Start (Template)
### Frontend
```bash
cd frontend
npm install
npm run dev
```

Vite after this change listens on the local network too and prints a `Network` URL like `http://192.168.1.x:5173` that you can open on your phone.

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 0.0.0.0:8000
```
