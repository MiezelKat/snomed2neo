FROM python:3

# R packages for my jupyter nb. needed for rpy2 package
RUN apt-get update

COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt