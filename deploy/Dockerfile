# CiciByte AI Media Factory — api + worker image. Powered by CiciByte Technology (https://cicibyte.com)
FROM python:3.12-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
       fonts-montserrat fonts-roboto fonts-open-sans fonts-bebas-neue fonts-lato \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 10001 --create-home --home-dir /home/mf --shell /usr/sbin/nologin mf \
    && mkdir -p /data && chown mf:mf /data

WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY backend ./backend
RUN pip install .

USER mf
ENV MF_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD mf healthcheck

CMD ["mf", "--help"]
