# sam-os MCP server — personal OS over stdio + internal scheduler
FROM python:3.12-slim

WORKDIR /app

# Install deps first (cached layer)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy code
COPY samos/ /app/samos/
COPY scripts/ /app/scripts/
COPY backup/ /app/backup/

# Run as non-root
RUN useradd -m -u 1000 samos
RUN chown -R samos:samos /app
USER samos

ENV PYTHONPATH=/app
ENV PYTHONIOENCODING=utf-8

# MCP server speaks over stdio; no ports exposed by default.
# If you also want SSE/HTTP, map a port and override CMD.
CMD ["python", "-u", "-m", "samos.server"]
