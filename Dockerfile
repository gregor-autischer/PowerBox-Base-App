ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python, Node.js, and required packages
RUN apk add --no-cache python3 py3-pip py3-aiohttp nodejs npm

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
COPY run.sh /
COPY app.py /app/

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
