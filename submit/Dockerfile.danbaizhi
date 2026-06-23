# Fusai docker image ? track 3 (Danbaizhi)
# DaoCloud proxy avoids Docker Hub 429 when???????is on.
FROM docker.m.daocloud.io/library/python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ \
    && pip install --no-cache-dir numpy mdtraj openmm \
    && python -c "import openmm; import mdtraj" \
    && apt-get purge -y gcc g++ \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy build stamp first so ACR layer cache invalidates on each publish.
COPY submit/build_info.json /app/submit/build_info.json
COPY submit/ /app/submit/
COPY Project/ /app/Project/
COPY agent/ /app/agent/
COPY submit/agent_code/danbaizhi/README.md /app/agent_code/README.md
COPY Project/code/ /app/agent_code/Project_code/
COPY Project/agent/ /app/agent_code/Project_agent/
COPY submit/run.sh /app/run.sh

RUN chmod +x /app/run.sh /app/submit/run.sh \
    && python -c "import openmm; import submit.tracks.registry as r; r.get_runner('danbaizhi')"

# LLM API — inject via ACR build args only (never commit real keys). See submit/LLM_API_KEY_ACR.md
ARG DANBAIZHI_LLM_API_KEY=""
ARG DANBAIZHI_LLM_BASE_URL=""
ARG DANBAIZHI_LLM_MODEL=""

ENV FUSAI_TRACK=danbaizhi
ENV DANBAIZHI_AUTO_PRIOR=1
ENV DANBAIZHI_LLM_API_KEY=${DANBAIZHI_LLM_API_KEY}
ENV DANBAIZHI_LLM_BASE_URL=${DANBAIZHI_LLM_BASE_URL}
ENV DANBAIZHI_LLM_MODEL=${DANBAIZHI_LLM_MODEL}
ENV SAISDATA=/saisdata
ENV SAISRESULT=/saisresult
ENV PYTHONUNBUFFERED=1

CMD ["sh", "/app/run.sh"]
