FROM  bitnami/spark:latest

WORKDIR /app

USER root

RUN mkdir -p /var/lib/apt/lists/partial && \
    apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip3 install pyspark kaggle

COPY Ecommerce_ETL.py /app/Ecommerce_ETL.py

CMD ["spark-submit", "--master", "spark://spark-master:7077", "/app/Ecommerce_ETL.py"]