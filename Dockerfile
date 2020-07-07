ARG ucs=latest
FROM docker-registry.knut.univention.de/phahn/ucs-aptbase:$ucs
ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8
COPY . /deb/
RUN echo 'deb [trusted=yes] file:///deb/ ./' >/etc/apt/sources.list.d/internal.list && \
	apt-get -qq update && \
	apt-get -qq install python-vnc-automate && \
	find /etc/apt/sources.list.d/internal.list /var/lib/apt/lists/ /var/cache/apt/archives/ /deb/ -not -name lock -type f -delete
ENTRYPOINT ["bash"]
