FROM fedora:latest

ARG claude_user=claude
ENV CLAUDE_USER=$claude_user

ARG claude_home_dir=/home/$claude_user

RUN useradd -d "$claude_home_dir" "$claude_user"

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
# https://github.com/anthropics/claude-code/blob/main/.devcontainer/Dockerfile
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

USER $claude_user

ENV NPM_CONFIG_PREFIX=$claude_home_dir/.local
RUN install -d "$claude_home_dir/.local"
RUN npm install -g @anthropic-ai/claude-code@latest

USER root

RUN install -o "$claude_user" -g "$claude_user" -d /workspace

COPY --chown=root:root --chmod=600 claude_sudoers /etc/sudoers.d/
RUN sed -E -i "s/^claude\\s/$claude_user /" /etc/sudoers.d/claude_sudoers

COPY --chown=root:root --chmod=0755 entrypoint.sh /
RUN install -o root -g root -m 700 -d /root
COPY rules.nft add_ip_ranges_to_nft_sets.py /root/

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]
