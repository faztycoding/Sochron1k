FROM python:3.14.7-bookworm@sha256:ecac9e212daacda8a702eae372fceebc0ee36f5805abe087880367e8d061fa5b AS sqlite-builder
WORKDIR /build
COPY services/runtime/sqlite.lock.json ./
COPY scripts/build-container-sqlite.py ./
RUN python build-container-sqlite.py

FROM python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f AS builder

ENV UV_NO_CACHE=1 \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN pip install --no-cache-dir uv==0.12.15
RUN python -c "from importlib.metadata import version; assert version('uv') == '0.12.15'" \
    && uv --version

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f

COPY --from=sqlite-builder /out/libsqlite3.so.0 /usr/local/lib/libsqlite3.so.0
COPY --from=sqlite-builder /out/sqlite-build.json /opt/sochron/sqlite-build.json
COPY services/runtime/sqlite.lock.json /opt/sochron/sqlite.lock.json
COPY scripts/check-container-sqlite.py /opt/sochron/check-sqlite.py
ENV LD_LIBRARY_PATH=/usr/local/lib
RUN ldconfig && python /opt/sochron/check-sqlite.py

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/services/api/src \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 sochron \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin sochron \
    && mkdir -p /app/data \
    && chown 10001:10001 /app/data

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --chown=10001:10001 services/api/src /app/services/api/src

USER 10001:10001
EXPOSE 8000

CMD ["uvicorn", "sochron1k.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
