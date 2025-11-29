FROM fedora:latest

RUN dnf -y --refresh upgrade && dnf clean all

RUN dnf -y --refresh install tinyproxy && dnf clean all

# Copy configuration files
COPY tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY allowlist /etc/tinyproxy/allowlist

# Expose proxy port
EXPOSE 8888

# Run tinyproxy in foreground
CMD ["tinyproxy", "-d"]
