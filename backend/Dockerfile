FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# `--require-hashes` AÇIQ verilir. pip həsh gördükdə onu onsuz da tələb edir,
# amma bayraq olmasa həshlər faylda təsadüfən itsə build SƏSSİZCƏ davam edər
# və yoxlanılmamış paketlər quraşdırılar. Bayraqla belə hal build-i dayandırır.
#
# requirements.txt ƏLLƏ redaktə olunmur — `scripts/lock-deps.sh` yaradır.
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY eval ./eval
COPY tests ./tests
COPY pytest.ini .

ENV PYTHONUNBUFFERED=1 \
    HF_CACHE_DIR=/models

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
