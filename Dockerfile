FROM eclipse-temurin:21-jre-jammy

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        apksigner ca-certificates gh git python3 python3-pip tzdata unzip zip \
    && ln -s /usr/bin/python3 /usr/local/bin/python \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /workspace
RUN chmod +x /workspace/scripts/container-entrypoint.sh /workspace/scripts/local_pipeline.sh
ENTRYPOINT ["/workspace/scripts/container-entrypoint.sh"]
