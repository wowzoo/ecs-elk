FROM docker.elastic.co/elasticsearch/elasticsearch:7.9.3

ARG CDK_REGION
ENV REGION $CDK_REGION

ADD elasticsearch.yml /usr/share/elasticsearch/config/

USER root
RUN chown elasticsearch:elasticsearch config/elasticsearch.yml

USER elasticsearch
WORKDIR /usr/share/elasticsearch

RUN bin/elasticsearch-plugin install -b discovery-ec2 && \
    bin/elasticsearch-plugin install -b repository-s3 && \
    sed -e '/^-Xm/s/^/#/g' -i /usr/share/elasticsearch/config/jvm.options