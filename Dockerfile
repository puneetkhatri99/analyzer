# Builds the dashboard, then serves it and the API on $PORT (Cloud Run sets it; 8080 by default).
FROM node:20-slim AS client
WORKDIR /client
COPY client/package*.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY --chown=user server/ server/
COPY --chown=user --from=client /client/dist client/dist
USER user
ENV APP_ENV=production
WORKDIR /home/user/app/server
# Keep --up-to in step with render.yaml.
CMD python -m app.cli migrate --up-to 17 && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'
