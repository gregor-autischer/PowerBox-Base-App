ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python and required packages
RUN apk add --no-cache python3 py3-pip py3-aiohttp

# Copy application files
COPY run.sh /
COPY app.py /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
