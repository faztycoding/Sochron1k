FROM python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f AS builder

ENV UV_NO_CACHE=1 UV_PYTHON_DOWNLOADS=0 SOURCE_DATE_EPOCH=1580601600
WORKDIR /build
RUN pip install --no-cache-dir uv==0.12.15 \
    && python -c "from importlib.metadata import version; assert version('uv') == '0.12.15'"
COPY pyproject.toml uv.lock .gitignore ./
RUN uv sync --frozen --no-dev --group build --no-install-project
COPY services/api/src/sochron1k /build/services/api/src/sochron1k
COPY services/worker/src/sochron_worker /build/services/worker/src/sochron_worker
RUN uv build --wheel --no-build-isolation --python /build/.venv/bin/python --out-dir /artifact \
    && uv export --locked --no-default-groups --no-emit-project --no-header --output-file /artifact/requirements.txt \
    && uv venv --no-project --python /usr/local/bin/python /opt/worker \
    && uv pip install --python /opt/worker/bin/python --require-hashes --only-binary :all: -r /artifact/requirements.txt \
    && uv pip install --python /opt/worker/bin/python --no-deps --no-index /artifact/sochron1k-0.1.0-py3-none-any.whl \
    && cd /artifact && sha256sum *.whl requirements.txt > SHA256SUMS

FROM python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f
ENV PATH="/opt/worker/bin:${PATH}" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 10001 sochron \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin sochron \
    && mkdir -p /worker/source /worker/state /worker/config \
    && chown 10001:10001 /worker/source /worker/state /worker/config \
    && chmod 700 /worker/source /worker/state /worker/config
COPY --from=builder /opt/worker /opt/worker
COPY --from=builder /artifact/SHA256SUMS /opt/artifact/SHA256SUMS
WORKDIR /worker
USER 10001:10001
ENTRYPOINT ["sochron-sync"]
CMD ["status"]
