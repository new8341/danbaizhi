# Default dockerfile alias (Danbaizhi)
FROM python:3.10-slim

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
