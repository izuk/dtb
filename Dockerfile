FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y \
        python3-full \
        curl \
        imagemagick \
        xz-utils \
        && \
    apt-get clean

RUN curl -fsSL https://install.typst.community/install.sh | sh

ENV TYPST_INSTALL="/root/.typst"
ENV PATH="$TYPST_INSTALL/bin:$PATH"

RUN python3 -m venv /dtb

WORKDIR /dtb

RUN bin/pip install discord.py

ADD ./bot.py .

ENV PYTHONUNBUFFERED=1

CMD ["bin/python3", "bot.py"]
