# Use official lightweight Python image
FROM python:3.12-slim as builder

# Set workspace directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Copy installed python dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY src/ /app/src/

# Update PATH to include user packages and set python module path
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app/src

# Expose default HTTP port for SSE transport
EXPOSE 8000

# Set entrypoint to our server script
ENTRYPOINT ["python", "src/server.py"]

# Default to stdio mode for Claude Desktop integration; can be overridden to "sse" at runtime
CMD ["--transport", "stdio"]
