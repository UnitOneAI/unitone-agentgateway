FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

# Copy startup script and fix line endings (Windows -> Unix)
COPY start-servers.sh .
RUN chmod +x start-servers.sh

# Environment variables for configuration
ENV MCP_HOST=0.0.0.0

# PII test server on 8000, tool-poisoning-test on 8010, rug-pull-test on 8020
EXPOSE 8000 8010 8020

# Run both servers
CMD ["./start-servers.sh"]
