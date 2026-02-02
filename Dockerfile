FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install backend requirements with increased timeout and retries
COPY backend/req/requirements.txt backend_req.txt
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r backend_req.txt
RUN pip install gunicorn

# Copy backend code
COPY backend/ .

# Copy tts_v6.2 for scheduling modules
COPY tts_v6.2/ /tts_v6.2

# Run Django migrations and collect static
ENV DJANGO_SETTINGS_MODULE=timetable_project.settings
RUN python manage.py migrate
RUN python manage.py collectstatic --noinput

# Install frontend dependencies and build
COPY frontend/ frontend/
WORKDIR /app/frontend
RUN npm install
RUN npm run build

# Go back to root
WORKDIR /app

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port
EXPOSE 8080

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]