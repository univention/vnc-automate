# vnc-automate

programmatic interface for VNC

_[TOC]_

# Docker image

Docker image with `vnc-automate` and [PyPI:`vncdotool`](https://pypi.org/project/vncdotool/) (univention/dist/vncdotool> is deprecated) based on `gitregistry.knut.univention.de/univention/dist/ucs-ec2-tools` from univention/dist/ucs-ec2-tools>.

# Pipeline

The pipeline builds the `vnc-automate` package from the source, creates the docker images and pushes the image to `gitregistry.knut.univention.de/univention/dist/vnc-automate` (for the main branch with the tag `latest`).

# Usage

See `ucs/test/utils/installation_test/installation.py` in univention/ucs>.

# Development

```sh
# create container, map current ucs-repo $HOME/git/ucs/test (for test utils) to /test
docker run --rm -it \
 -v "$HOME/ec2:$HOME/ec2:ro" \
 -v "$HOME/git/ucs/test:/test" \
 -w /test \
 --dns 192.168.0.124 \
 --dns 192.168.0.97 \
 --dns-search knut.univention.de \
 gitregistry.knut.univention.de/univention/dist/vnc-automate \
 bash

# now in the container, start an installation on a pre-defined machine
python utils/installation_test/vnc-install-ucs.py --vnc isala:2 --language deu --role basesystem --fqdn base
```

# Testing

```
mkdir dump/
VNCAUTOMATE_DEBUG=logging.yaml \
VNCAUTOMATE_TMP=1 \
python3 -m vncautomate.cli \
	--log debug \
	--dump-boxes dump/boxes.png \
	--dump-dir dump/ \
	--dump-screen dump/screen.png \
	--dump-x-gradients dump/x.png \
	--dump-y-gradients dump/y.png \
	--lang eng tests/login.png Username
```
