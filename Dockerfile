FROM docker-registry.knut.univention.de/ucs-ec2-tools
ENV LANG C.UTF-8
COPY ["python*-vnc-automate_*.deb", "/"]
RUN apt-get -qq update \
    && mkdir -p /var/log/apt/ \
	&& apt-get -y -f install --no-install-recommends /python*-vnc-automate_*.deb vncsnapshot \
    && apt-get -y install --no-install-recommends python3-pip python-pip python-setuptools python3-setuptools python-wheel python3-wheel \
    && pip install vncdotool \
    && pip3 install vncdotool \
	&& rm -rf /usr/share/doc /usr/share/man /usr/share/locale /usr/share/info /var/cache/apt /var/lib/apt/lists /var/log /var/lib/dpkg/*-old
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["bash"]
