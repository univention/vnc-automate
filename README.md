# vnc-automate

programmatic interface for VNC

# docker-registry.knut.univention.de/ucs-vnc-tools

Docker image with `vnc-automate` and (pip) vncdotool (univention/dist/vncdotool> is deprecated) based on `docker-registry.knut.univention.de/ucs-ec2-tools`.

# Pipeline

The pipeline builds the `vnc-automate package` from the source, creates the docker images and pushes the image to `docker-registry.knut.univention.de` (for the main branch with tha latest tag)

# Usage

See `ucs/test/utils/installation_test/installation.py` in univention/ucs>.

# development

```
docker pull docker-registry.knut.univention.de/ucs-vnc-tools
# create container, map current ucs-repo $HOME/git/ucs/test (for test utils) to /test
docker run --rm -it -w /test -v $HOME/git/ucs/test:/test \
 -v $HOME/ec2:$HOME/ec2:ro --dns 192.168.0.124 \
 --dns 192.168.0.97 --dns-search knut.univention.de \
 docker-registry.knut.univention.de/ucs-vnc-tools bash

# now in the container, start an installation on a pre-defined machine
python utils/installation_test/vnc-install-ucs.py --vnc isala:2 --language deu --role basesystem --fqdn base"
```
