FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY sdd ./sdd
RUN python -m pip install --no-cache-dir -r sdd/mcp/requirements.txt

ENV SDD_MCP_REGISTRY=/app/registry.json
EXPOSE 8765

CMD ["python", "-m", "sdd.mcp.server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8765", "--path", "/mcp"]
