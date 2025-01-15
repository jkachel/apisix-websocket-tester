FROM debian:bookworm
LABEL maintainer "ODL DevOps <mitx-devops@mit.edu>"
EXPOSE 7766

# Add package files, install updated node and pip
WORKDIR /tmp

# Install packages
COPY apt.txt /tmp/apt.txt
RUN apt-get update
RUN apt-get install -y $(grep -vE "^\s*#" apt.txt  | tr "\n" " ")
RUN apt-get clean && apt-get purge

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

# Project setup
RUN mkdir /src
COPY . /src

RUN adduser --disabled-password --gecos "" mitodl
RUN chown -R mitodl:mitodl /src
USER mitodl

WORKDIR /src

RUN uv python install 3.12
RUN uv sync

CMD ["uv", "run", "-v", "server.py"]
