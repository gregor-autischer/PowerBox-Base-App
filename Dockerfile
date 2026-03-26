ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python, Node.js, and required packages
RUN apk add --no-cache \
    python3 py3-pip py3-aiohttp \
    nodejs npm \
    openssh \
    ttyd \
    tmux \
    bash-completion \
    nano \
    vim

# Set working directory
WORKDIR /app

# Copy package files and install frontend dependencies
COPY package.json ./
RUN npm install

# Copy frontend source and config files
COPY frontend/ ./frontend/
COPY vite.config.js tailwind.config.js postcss.config.js ./

# Build frontend assets
RUN npm run build

# Copy application files
COPY app.py /app/

# Copy rootfs (s6-overlay services, sshd_config)
COPY rootfs /

# Ensure s6 service scripts are executable
RUN chmod a+x \
    /etc/s6-overlay/s6-rc.d/powerhaus-app/run \
    /etc/s6-overlay/s6-rc.d/powerhaus-app/finish \
    /etc/s6-overlay/s6-rc.d/init-ssh/run \
    /etc/s6-overlay/s6-rc.d/sshd/run \
    /etc/s6-overlay/s6-rc.d/sshd/finish \
    /etc/s6-overlay/s6-rc.d/ttyd/run
