FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        g++ \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# MLX CPU JIT emits typedefs that GCC treats as errors; -fpermissive downgrades to warnings.
RUN printf '#!/bin/sh\nexec /usr/bin/g++ -fpermissive "$@"\n' > /usr/local/bin/g++ \
    && chmod +x /usr/local/bin/g++

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

ARG MLX_BACKEND=cpu
RUN uv pip install --no-cache-dir "mlx[${MLX_BACKEND}]"

# Ensure mlx shared libs are discoverable at runtime on Linux
ENV LD_LIBRARY_PATH="/opt/venv/lib/python3.13/site-packages/mlx/lib:${LD_LIBRARY_PATH}"

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
