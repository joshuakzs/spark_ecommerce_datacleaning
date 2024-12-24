# spark_ecommerce_datacleaning

## Version 1
Combine and clean 21 csv files (totaling 14-15MB) using PySpark on Databricks. This project is for me to learn and practise using Apache Spark. 
Data is taken from:
https://www.kaggle.com/datasets/oleksiimartusiuk/e-commerce-data-shein/data
This data taken is stored in the input_folder in this repository. If not running the code on databricks, the code cell used to read the data must be edited to change the directory to the correct folder.
Output data of the ETL process is in the repository as well (in csv format).

I wrote PySpark code on a databricks notebook to do my data cleaning. I had to do a little of each of the following for the data:
* Columns Renaming
* Reformatting data
* Missing Data Imputation
* Dropping Redundant Columns
* Dealing with duplicates
* Feature Engineering

## Version 2
Approximately 2 months after completing version 1, I learnt the basics of Docker. As practice, I will be using Docker to dockerise my code. Below are the changes made:
* Instead of using Databricks, I will be using Spark on my local machine.
* Instead of having CSVs already downloaded before running the cleaning script, we will use command line to download the csvs
* We will use a docker-compose.yml file for a simple ETL process - to collect data, clean the data, and then output the data. The spark docker image we will be using is from: https://hub.docker.com/r/bitnami/spark

To run Version_2, do the following steps:
1. In terminal, change directory to **Version_2** folder
2. Make sure Docker App is running on computer
3. Run **docker-compose build** to build the docker images
4. Run **docker-compose up --scale spark-worker=4**. Note that we are using 4 spark workers and 1 spark master. We can change the number base on number of cpus available.