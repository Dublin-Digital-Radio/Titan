FROM python:3.9-slim-bullseye as base

RUN useradd -ms /bin/bash titan
WORKDIR /home/titan/Titan

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


FROM base as build

ARG VIRTUAL_ENV="/home/titan/venv"
ENV VIRTUAL_ENV=$VIRTUAL_ENV
ARG PATH="$VIRTUAL_ENV/bin":$PATH
ENV PATH=$PATH

RUN apt update && \
  apt install --no-install-recommends -y \
    build-essential \
    python-dev  && \
  rm -rf /var/lib/apt/lists/*

RUN python -mvenv $VIRTUAL_ENV
RUN pip install -U pip wheel


FROM build as build-discordbot

ARG VIRTUAL_ENV="/home/titan/venv"
ENV VIRTUAL_ENV=$VIRTUAL_ENV
ARG PATH="$VIRTUAL_ENV/bin":$PATH
ENV PATH=$PATH

COPY requirements/requirements.discordbot.txt .
RUN pip install -r requirements.discordbot.txt


FROM build as build-webapp

ARG VIRTUAL_ENV="/home/titan/venv"
ENV VIRTUAL_ENV=$VIRTUAL_ENV
ARG PATH="$VIRTUAL_ENV/bin":$PATH
ENV PATH=$PATH

COPY requirements/requirements.webapp.txt .
RUN pip install -r requirements.webapp.txt


FROM base as run-discordbot

ARG VIRTUAL_ENV="/home/titan/venv"
ENV VIRTUAL_ENV=$VIRTUAL_ENV
ARG PATH="$VIRTUAL_ENV/bin":$PATH
ENV PATH=$PATH
ENV DATABASE_URL='postgresql://titan:titan@localhost:5432/titan'
ENV REDIS_URL='redis://localhost'

COPY --from=build-discordbot /home/titan/venv /home/titan/venv
COPY discordbot discordbot/

USER titan
WORKDIR /home/titan/Titan/discordbot
CMD ["python", "run.py"]


FROM base as run-webapp

ARG VIRTUAL_ENV="/home/titan/venv"
ENV VIRTUAL_ENV=$VIRTUAL_ENV
ARG PATH="$VIRTUAL_ENV/bin":$PATH
ENV PATH=$PATH
ENV DATABASE_URL='postgresql://titan:titan@localhost:5432/titan'
ENV REDIS_URL='redis://localhost'

COPY --from=build-webapp /home/titan/venv /home/titan/venv

COPY webapp webapp/

RUN cd webapp && /home/titan/venv/bin/python bin/tr_compile.py

USER titan
WORKDIR /home/titan/Titan/webapp
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:8080", "titanembeds.app:app"]


