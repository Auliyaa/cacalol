FROM ubuntu:22.04

RUN echo 'APT::Install-Suggests "0";' >> /etc/apt/apt.conf.d/00-docker
RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf.d/00-docker
RUN DEBIAN_FRONTEND=noninteractive \
  apt-get update \
  && apt-get install -y python3 python3-pip git ffmpeg\
  && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash apprunner

RUN pip3 install yt_dlp\
    && pip3 install asyncio\
    && pip3 install typing\
    && pip3 install dataclasses\
    && pip3 install discord

USER apprunner

RUN cd && git clone https://github.com/Auliyaa/cacalol.git

ENTRYPOINT /usr/bin/python3 /home/apprunner/cacalol/bot.py
