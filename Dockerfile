FROM python:3.7-alpine
RUN mkdir -p /aiotunnel
COPY requirements.txt /aiotunnel
RUN pip install -r /aiotunnel/requirements.txt --no-cache-dir
ADD . /aiotunnel
WORKDIR /aiotunnel
CMD aiotunnel server -r
