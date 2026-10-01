FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY agents/agentcore-runtime/pyproject.toml /app/pyproject.toml
COPY agents/agentcore-runtime/src /app/src
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 agent \
    && chown -R agent:agent /app
USER agent

EXPOSE 8080
CMD ["python", "-m", "supervisor_agent.app"]