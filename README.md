# vnc-automate

programmatic interface for VNC

# docker-registry.knut.univention.de/ucs-vnc-tools

Docker image with `vnc-automate` and univention/dist/vncdotool> (pip) based on `docker-registry.knut.univention.de/ucs-ec2-tools`.

# Pipeline

The pipeline builds the `vnc-automate package` from the source, creates the docker images and pushes the image to `docker-registry.knut.univention.de` (for the main branch with tha latest tag)

# Usage

See `ucs/test/utils/installation_test/installation.py` in univention/ucs>.
