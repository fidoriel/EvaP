FROM python:3.10

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# install python deps
RUN apt-get update -y && apt-get install -y libpq-dev

RUN python3 -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"
COPY requirements.txt requirements-dev.txt ./
RUN pip install requirements-dev.txt

# install node deps
RUN apt-get install -y nodejs npm
COPY package.json package-lock.json ./
RUN npm ci

COPY ./ /app/
RUN cp deployment/manage_autocompletion.sh /etc/bash_completion.d/
ENTRYPOINT [ "/app/entrypoint.sh" ]