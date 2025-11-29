FROM fedora:latest

# Remove option that says "don't install documentation"
RUN sed -E -i '/^tsflags\s*=\s*nodocs\s*$/d' /etc/dnf/dnf.conf

# Updates
RUN dnf -y --refresh upgrade && dnf clean all

# Packages required for isolation
RUN dnf -y --refresh install \
    jq \
    nftables \
    python3 \
    util-linux \
    && dnf clean all

# Packages required for Claude
RUN dnf -y --refresh install \
    nodejs-npm \
    && dnf clean all

# Packages taken from the devcontainer
# https://github.com/anthropics/llm-code/blob/main/.devcontainer/Dockerfile
RUN dnf -y --refresh install \
    gh \
    git \
    man-db \
    man-pages \
    unzip \
    # nano \
    && dnf clean all

# Nice-to-haves when interactive
RUN dnf -y --refresh install \
    bat \
    bind-utils \
    direnv \
    fd-find \
    fzf \
    iproute \
    iputils \
    less \
    lsof \
    # ping \
    procps-ng \
    ripgrep \
    tree \
    vim-enhanced \
    zoxide \
    && dnf clean all

ARG LLM_USER
ARG LLM_HOME_DIR

ENV LLM_USER=$LLM_USER
ENV LLM_HOME_DIR=$LLM_HOME_DIR

RUN useradd -d "$LLM_HOME_DIR" "$LLM_USER"

USER $LLM_USER

ENV NPM_CONFIG_PREFIX=$LLM_HOME_DIR/.local
RUN install -d "$LLM_HOME_DIR/.local"
RUN npm install -g @anthropic-ai/claude-code@latest

USER root

RUN install -o "$LLM_USER" -g "$LLM_USER" -d /workspace

COPY --chown=root:root --chmod=600 llm_sudoers /etc/sudoers.d/
RUN sed -E -i "s/^llm\\s/$LLM_USER /" /etc/sudoers.d/llm_sudoers

COPY --chown=root:root --chmod=0755 entrypoint.sh /
RUN install -o root -g root -m 700 -d /root
COPY rules.nft add_ip_ranges_to_nft_sets.py /root/

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]
