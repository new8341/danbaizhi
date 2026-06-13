# Root Dockerfile for ACR cloud build (same as submit/Dockerfile.danbaizhi)
FROM registry.cn-shanghai.aliyuncs.com/tcc-public/python:3

RUN pip install --no-cache-dir numpy mdtraj -i https://pypi.tuna.tsinghua.edu.cn/simple

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
