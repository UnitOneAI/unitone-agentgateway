FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

# Copy startup script and fix line endings (Windows -> Unix)
COPY start-server.sh .
RUN chmod +x start-server.sh

# Environment variables for configuration
ENV MCP_HOST=0.0.0.0

# PII test server on 8000, tool-poisoning-test on 8010, rug-pull-test on 8020
EXPOSE 8000 8010 8020

# Run all servers (SERVER_TYPE=all runs PII, Tool Poisoning, and Rug Pull servers)
ENV SERVER_TYPE=all
CMD ["./start-server.sh"]
