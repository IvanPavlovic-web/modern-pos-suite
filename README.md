# POS Sistem

POS application with a React cashier interface, Django REST API, PostgreSQL, Redis-backed WebSockets, receipt printing, refunds, and reports.

## Local setup

Requirements: Docker Desktop and Docker Compose.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:5173`. The API is at `http://localhost:8000`.

To load demo users and products:

```powershell
docker compose exec backend python manage.py seed_data
```

Demo accounts are `admin/admin123`, `manager/manager123`, and `cashier1/cashier123`. Do not use these passwords outside a local demo.

## Free demo deployment

Suggested services: Render Static Site for the frontend, Render Web Service for Django, Neon for PostgreSQL, and Upstash for Redis. Neon and Upstash have ongoing free plans. Render's free web service sleeps after 15 minutes without traffic and can take about a minute to wake. WebSockets can disconnect while idle. This setup is for demos, not a shop that needs an always-on till.

1. Create a Neon project and an Upstash Redis database. Keep their connection details private.
2. Create a Render Web Service from this repository. Set the root directory to `backend`, use the `Docker` runtime, and leave the start command empty. The Docker image runs migrations and starts Daphne on Render's `PORT`.
3. Add these backend environment variables in Render:
   - `DJANGO_SECRET_KEY`: a newly generated secret
   - `DJANGO_DEBUG`: `False`
   - `DJANGO_ALLOWED_HOSTS`: the Render backend hostname
   - `CORS_ALLOWED_ORIGINS`: the Render frontend URL
   - `CSRF_TRUSTED_ORIGINS`: the Render frontend URL
   - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`: values from Neon
   - `POSTGRES_SSLMODE`: `require`
   - `REDIS_URL`: the Upstash `rediss://` connection URL
4. Create a Render Static Site. Set root directory to `frontend`, build command to `npm install && npm run build`, and publish directory to `dist`. Add `VITE_API_URL=https://<backend-host>` and `VITE_WS_URL=wss://<backend-host>` as build environment variables.
5. Add a Render rewrite from `/*` to `/index.html` with status `200` for React Router routes. Set the final frontend URL in the backend CORS and CSRF variables, then redeploy the backend.
6. Create an operator account with `python manage.py createsuperuser` or create users and assign the `cashier`, `manager`, or `admin` group in Django admin. Do not run the demo seed command on a real database.

Free plans have low quotas and no production guarantees. Neon Free currently limits each project to 0.5 GB and 100 CU-hours per month. Upstash Free currently includes 256 MB and 500,000 commands per month. Render's free filesystem is temporary, so local backup files are not durable. Check provider limits before deployment.

## Reddit discussions

Reddit recommendations are anecdotal and older than current provider plans. Threads mention Render and separating the Django app from its database; WebSocket discussions also warn that sleeping free services interrupt connections.

- [Django hosting with PostgreSQL](https://www.reddit.com/r/django/comments/1dp2jnw/how_and_where_can_i_host_my_django_projectwith/)
- [Django hosting recommendations](https://www.reddit.com/r/django/comments/18zhqtu/which_cheap_hosting_service_do_you_recommend/)
- [Free WebSocket hosting discussion](https://www.reddit.com/r/webdev/comments/18v1ggf/free_websocket_hosting_doesnt_exist/)

Current limits: [Render Free](https://render.com/docs/free), [Neon pricing](https://neon.com/pricing), [Upstash Redis pricing](https://upstash.com/pricing/redis).
