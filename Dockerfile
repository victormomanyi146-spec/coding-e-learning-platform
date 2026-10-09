FROM node:24-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_BUILD_BASE=/static/react/
ENV VITE_BUILD_BASE=${VITE_BUILD_BASE}
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt
COPY backend/ /app/backend/
RUN mkdir -p /app/backend/templates/react_app /app/backend/static/react/assets
COPY --from=frontend-build /app/frontend/dist/index.html /tmp/react-index.html
COPY --from=frontend-build /app/frontend/dist/assets/ /app/backend/static/react/assets/
COPY deployment/prepare_react_template.py /app/prepare_react_template.py
RUN python /app/prepare_react_template.py \
    /tmp/react-index.html \
    /app/backend/templates/react_app/index.html
COPY deployment/start-unified.sh /app/start-unified.sh
RUN chmod +x /app/start-unified.sh
WORKDIR /app/backend

ENV UNIFIED_REACT_FRONTEND=True
EXPOSE 10000
CMD ["bash", "/app/start-unified.sh"]
