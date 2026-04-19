FROM node:22-bookworm AS node

FROM python:3.12-bookworm AS data_camp_qa_gen

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code \
    PLAYWRIGHT_VERSION=1.58.2 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PNPM_HOME=/home/agent/.local/share/pnpm \
    PNPM_STORE_DIR=/home/agent/.local/share/pnpm/store \
    NPM_CONFIG_CACHE=/home/agent/.npm \
    XDG_DATA_HOME=/home/agent/.local/share \
    PATH=/home/agent/.local/share/pnpm:/usr/local/bin:${PATH}

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git curl wget ca-certificates gnupg lsb-release \
    unzip zip jq tree ripgrep fd-find tmux neovim vim shellcheck \
    pkg-config openssl sudo \
    chromium chromium-driver firefox-esr \
    xvfb xauth dbus dbus-x11 \
    fonts-liberation fonts-noto-color-emoji \
    postgresql-15 postgresql-client-15 postgresql-contrib-15 redis-tools \
    postgresql-15-postgis-3 postgresql-15-postgis-3-scripts \
    fzf zsh \
    && rm -rf /var/lib/apt/lists/*

# Bring in Node/npm/npx from official Node image
COPY --from=node /usr/local /usr/local

# Create runtime user
RUN groupadd agent \
    && useradd -m -g agent agent \
    && mkdir -p /code \
        /home/agent/.local/share/pnpm/store \
        /home/agent/.npm \
        /home/agent/.local/share \
    && chown -R agent:agent /code /home/agent

# Node tooling
RUN npm install -g \
      pnpm@10 \
      playwright@${PLAYWRIGHT_VERSION} \
      @playwright/test@${PLAYWRIGHT_VERSION} \
    && pnpm config set store-dir "$PNPM_STORE_DIR" \
    && node --version \
    && npm --version \
    && pnpm --version \
    && playwright --version

# Playwright browser bundle + deps
RUN playwright install --with-deps chromium firefox webkit

# Handy wrapper for headed browser runs
RUN cat > /usr/local/bin/with-display <<'EOF_SCRIPT'
#!/bin/sh
exec xvfb-run -a --server-args="-screen 0 2560x1600x24" "$@"
EOF_SCRIPT
RUN chmod +x /usr/local/bin/with-display

RUN npm install -g \
      @openai/codex 

# switch
ARG USER=agent
ARG HOME=/home/$USER
RUN chown -R agent:agent /home/agent /code

USER agent
WORKDIR /code




# Python tooling
RUN pip install --no-cache-dir \
    selenium==4.41.0 \
    pytest==9.0.2 \
    pytest-cov==7.1.0 \
    pytest-xdist==3.8.0 \
    webdriver-manager==4.0.2



# Claude install
RUN curl -fsSL https://claude.ai/install.sh | bash
RUN echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Install third-party skills with the `npx skills add <github-url>` workflow.
RUN npx --yes skills@1.4.6 add https://github.com/shadcn/ui \
      --skill shadcn \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/vercel-labs/next-skills \
      --skill next-best-practices \
      --skill next-cache-components \
      --skill next-upgrade \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/vercel-labs/next-browser \
      --skill next-browser \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/wshobson/agents \
      --skill nodejs-backend-patterns \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/supabase/agent-skills \
      --skill supabase-postgres-best-practices \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/github/awesome-copilot \
      --skill postgresql-optimization \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/github/awesome-copilot \
      --skill python-mcp-server-generator \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/wshobson/agents \
      --skill python-testing-patterns \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/wshobson/agents \
      --skill python-design-patterns \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/wshobson/agents \
      --skill python-code-style \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy \
    && npx --yes skills@1.4.6 add https://github.com/wshobson/agents \
      --skill python-anti-patterns \
      --agent codex \
      --agent claude-code \
      --global \
      --yes \
      --copy


COPY .claude_ $HOME/.claude
COPY .claude.json_ $HOME/.claude.json
RUN echo `whoami`
RUN echo `groups`
USER root
RUN chown -R agent:agent /home/agent/.claude
RUN chown -R agent:agent /home/agent/.claude.json
USER agent

EXPOSE 8921
EXPOSE 8922
EXPOSE 8923


CMD ["bash"]
