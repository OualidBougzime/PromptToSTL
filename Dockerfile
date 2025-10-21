# Utiliser une base stable avec les bons paquets
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Dépendances système requises par CadQuery/OpenCascade
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglu1-mesa \
    libglib2.0-0 \
    libxrender1 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./backend /app

EXPOSE 8000
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000","--reload"]
