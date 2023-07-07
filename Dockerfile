FROM docker-registry.knut.univention.de/ucs-ec2-tools
ENV LANG C.UTF-8
COPY ["python3-vnc-automate_*.deb", "/"]
RUN apt-get -qq update \
    && mkdir -p /var/log/apt/ \
    && apt-get -q --assume-yes -f install /python3-vnc-automate_*.deb vncsnapshot \
    && apt-get -q --assume-yes install --no-install-recommends \
        python3-pil \
        python3-pip \
        python3-pycryptodome \
        python3-scipy \
        python3-setuptools \
        python3-twisted \
        python3-wheel \
        python3-yaml \
    && pip3 install vncdotool==1.2.0 \
    && rm -rf \
        /usr/share/doc \
        /usr/share/info \
        /usr/share/locale \
        /usr/share/man \
        /var/cache/apt \
        /var/lib/apt/lists \
        /var/log \
        /var/lib/dpkg/*-old /*.deb
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["bash"]
