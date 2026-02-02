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
RUN ls -la dist/

# Copy built frontend files to static location
RUN mkdir -p /app/static/frontend && cp -r dist/* /app/static/frontend/ && echo "=== Frontend files copied ===" && ls -laR /app/static/frontend/

# Go back to root
WORKDIR /app

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Verify frontend files are in place and check permissions
RUN echo "=== Verifying /app/static/frontend contents ===" && ls -laR /app/static/frontend/ || echo "ERROR: Directory not found!"
RUN echo "=== Testing if index.html exists ===" && test -f /app/static/frontend/index.html && echo "index.html found!" || echo "ERROR: index.html NOT FOUND!"
RUN echo "=== Checking file permissions ===" && ls -la /app/static/frontend/index.html
RUN echo "=== Testing if nginx can read index.html ===" && cat /app/static/frontend/index.html > /dev/null && echo "File is readable!" || echo "ERROR: Cannot read file!"

# Expose port
EXPOSE 8080

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]