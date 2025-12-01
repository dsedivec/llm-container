FROM fedora:latest

# Remove option that says "don't install documentation"
RUN sed -E -i '/^tsflags\s*=\s*nodocs\s*$/d' /etc/dnf/dnf.conf

# Updates
RUN dnf -y --refresh upgrade && dnf clean all

# Packages required for isolation
RUN dnf -y --refresh install \
    jq \
    iproute \
    nftables \
    python3 \
    tinyproxy \
    util-linux \
    && dnf clean all

# Packages required for Claude
RUN dnf -y --refresh install \
    nodejs-npm \
    && dnf clean all

# Packages taken from the devcontainer
# https://github.com/anthropics/claude-code/blob/main/.devcontainer/Dockerfile
RUN dnf -y --refresh install \
    gh \
    git \
    man-db \
    man-pages \
    unzip \
    # nano \
    && dnf clean all

ARG LLM_USER=llm
ARG LLM_HOME_DIR=/home/${LLM_USER}

ENV LLM_USER=$LLM_USER
ENV LLM_HOME_DIR=$LLM_HOME_DIR

RUN useradd -d "$LLM_HOME_DIR" "$LLM_USER"

USER $LLM_USER

ENV NPM_CONFIG_PREFIX=$LLM_HOME_DIR/.local
RUN install -d "$LLM_HOME_DIR/.local"

RUN npm install -g @anthropic-ai/claude-code@latest
RUN npm install -g @openai/codex

USER root

# Nice-to-haves when interactive
RUN dnf -y --refresh install \
    bat \
    bind-utils \
    direnv \
    fd-find \
    fzf \
    iputils \
    less \
    lsof \
    # ping \
    procps-ng \
    ripgrep \
    rsync \
    tree \
    vim-enhanced \
    zoxide \
    && dnf clean all

COPY --chown=root:root --chmod=600 llm_sudoers /etc/sudoers.d/
RUN sed -E -i "s/^llm\\s/$LLM_USER /" /etc/sudoers.d/llm_sudoers

COPY --chown=root:root --chmod=0755 entrypoint.sh /
COPY --chown=root:root --chmod=0600 rules.nft /root/

# Copy tinyproxy configs
COPY --chown=root:root --chmod=644 tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY --chown=root:root --chmod=644 blocklist /etc/tinyproxy/blocklist
# Create tinyproxy log directory and log file (world-readable)
RUN install -d -m 755 -o tinyproxy -g tinyproxy /var/log/tinyproxy && \
    install -m 644 -o tinyproxy -g tinyproxy /dev/null /var/log/tinyproxy/tinyproxy.log

RUN install -d -m 755 -o "$LLM_USER" -g "$LLM_USER" "$LLM_HOME_DIR/.bashrc.d"
COPY --chown=$LLM_USER:$LLM_USER --chmod=0600 llm_bashrc $LLM_HOME_DIR/.bashrc.d/50_persist_bashrc
RUN install -d -m 700 -o "$LLM_USER" -g "$LLM_USER" "$LLM_HOME_DIR/.persist"
VOLUME ["$LLM_HOME_DIR/.persist"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]
