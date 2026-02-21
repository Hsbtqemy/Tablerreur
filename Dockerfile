# ── Build stage ──
FROM python:3.11-slim AS builder

WORKDIR /app

# Outils de compilation pour les éventuelles extensions C (pandas, rapidfuzz…)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements-web.txt .

# Installer les dépendances Python du cœur (pyproject.toml, sans PySide6)
# et les dépendances web (fastapi, uvicorn, python-multipart)
RUN pip install --no-cache-dir \
    "pandas>=2.1" \
    "openpyxl>=3.1" \
    "pyyaml>=6.0" \
    "rapidfuzz>=3.6" \
    "chardet>=5.0" \
    "httpx>=0.27" \
    -r requirements-web.txt

# ── Runtime stage ──
FROM python:3.11-slim

WORKDIR /app

# Copier les packages Python installés depuis le builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copier les sources de l'application
# (on n'installe pas le paquet pour éviter PySide6 ; PYTHONPATH suffit)
COPY src/ src/

# Variables d'environnement
ENV PYTHONPATH=/app/src
ENV TABLERREUR_ENV=prod
ENV TABLERREUR_MAX_UPLOAD_MB=50
ENV TABLERREUR_CORS_ORIGINS=""
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check — attend que l'API réponde sur /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Lancer uvicorn directement (le launcher ouvrirait un navigateur, indésirable en prod)
CMD ["uvicorn", "spreadsheet_qa.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
