FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    pulseaudio \
    pulseaudio-utils \
    alsa-utils \
    ffmpeg \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    chromium-browser \
    chromium-browser-l10n \
    python3.11 \
    python3.11-dev \
    python3-pip \
    supervisor \
    curl \
    wget \
    dbus \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp/pulse /var/run/dbus /var/run/pulse /root/.config/pulse /var/log/supervisor
RUN chmod 777 /tmp/pulse /var/run/pulse
RUN dbus-uuidgen > /var/lib/dbus/machine-id
RUN adduser root pulse-access 2>/dev/null || true

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt
RUN pip3 install playwright==1.44.0
RUN playwright install chromium
RUN playwright install-deps chromium

COPY config/pulse-default.pa /etc/pulse/system.pa
COPY config/supervisord.conf /etc/supervisor/conf.d/bot.conf
COPY src/ /app/src/

WORKDIR /app

ENV DISPLAY=:99
ENV PULSE_SERVER=unix:/tmp/pulse/native
ENV HOME=/root
ENV PYTHONPATH=/app
ENV XDG_RUNTIME_DIR=/tmp

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]