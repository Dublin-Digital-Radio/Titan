FROM python:3.9-slim-bullseye as base

RUN useradd -ms /bin/bash titan
WORKDIR /home/titan/Titan

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


FROM golang:1.19-bullseye as overmind-build

RUN go install github.com/DarthSim/overmind/v2@latest


FROM base as build

ENV VIRTUAL_ENV "/home/titan/venv"
ENV PATH="$VIRTUAL_ENV/bin":$PATH

RUN apt update && \
  apt install --no-install-recommends -y \
    build-essential \
    python-dev  && \
  rm -rf /var/lib/apt/lists/*

RUN python -mvenv $VIRTUAL_ENV
RUN pip install -U pip wheel


FROM build as build-discordbot

COPY requirements/requirements.discordbot.txt .
RUN pip install -r requirements.discordbot.txt


FROM build as build-webapp

COPY requirements/requirements.webapp.txt .
RUN pip install -r requirements.webapp.txt


FROM base as run-base

RUN apt update && \
  apt install --no-install-recommends -y \
    tmux && \
  rm -rf /var/lib/apt/lists/*

COPY --from=overmind-build /go/bin/overmind /usr/local/bin/


FROM run-base as run-webapp

COPY --from=build-webapp /home/titan/venv /home/titan/venv

COPY webapp webapp/

RUN cd webapp && /home/titan/venv/bin/python bin/tr_compile.py

WORKDIR /home/titan
COPY Procfile .

#USER titan

CMD ["overmind", "start"]


FROM run-base as run-discordbot
COPY --from=build-discordbot /home/titan/venv /home/titan/venv
COPY discordbot discordbot/


