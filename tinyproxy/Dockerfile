FROM fedora:latest

RUN dnf -y --refresh upgrade && dnf clean all

RUN dnf -y --refresh install tinyproxy && dnf clean all

COPY --chmod=0644 tinyproxy.conf /etc/tinyproxy/tinyproxy.conf

# Expose proxy port
EXPOSE 8888

# Run tinyproxy in foreground
CMD ["tinyproxy", "-d"]
