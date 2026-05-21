FROM python:3.11-slim

# WeasyPrint system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying source so layer is cached
COPY pyproject.toml ./
RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir \
    fastapi uvicorn[standard] langchain langgraph langfuse anthropic httpx pydantic \
    supabase python-dotenv weasyprint Markdown comtradeapicall world_trade_data \
    redis pyyaml pandas rich resend paddle-python-sdk apscheduler \
    "sentry-sdk[fastapi]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
