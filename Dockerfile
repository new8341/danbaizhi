# ACR: python:3.10-slim ¡ª drugclip/baxiangfenzi: overseas build ON; danbaizhi: overseas OFF.
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ \
    && pip install --no-cache-dir numpy mdtraj \
    && apt-get purge -y gcc g++ \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY submit/ /app/submit/
COPY Project/ /app/Project/
COPY agent/ /app/agent/
COPY submit/run.sh /app/run.sh

RUN chmod +x /app/run.sh /app/submit/run.sh

ENV FUSAI_TRACK=danbaizhi
ENV SAISDATA=/saisdata
ENV SAISRESULT=/saisresult
ENV PYTHONUNBUFFERED=1

CMD ["sh", "/app/run.sh"]
