# MineGuard Command Center

Real-time mining rescue operations dashboard prototype based on the MineGuard specification.

## Project structure

```text
README.md
src/
  backend/
    main.py
    requirements.txt
  frontend/
    index.html
    styles.css
    app.js
```

## Frontend

The frontend is a static dashboard prototype with simulated telemetry.

```bash
cd src/frontend
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Backend

The backend is a FastAPI scaffold with REST endpoints and a WebSocket telemetry stream.

```bash
cd src/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

Available endpoints:

- `GET /health`
- `GET /api/workers`
- `GET /api/alerts/active`
- `GET /api/mine/topology`
- `GET /api/history`
- `WS /ws/dashboard`

## Notes

The current frontend still runs independently so it can be opened quickly during demos. The backend mirrors the simulated operational data and is ready to be wired into the dashboard when live data integration begins.
