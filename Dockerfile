FROM python:3.13-slim

COPY requirements.txt /tmp/requirements.txt
RUN mkdir /app /config && \
    python3 -m venv /venv && \
    . /venv/bin/activate && \
    pip install --no-cache -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt
COPY src/. /app/
COPY config/. /config/

ENV VIRTUAL_ENV /venv
ENV PATH $VIRTUAL_ENV/bin:$PATH
ENV CONFIG_DIR /config

WORKDIR /app

CMD ["uvicorn", "main:app", "--host", "::", "--port", "8000"]

