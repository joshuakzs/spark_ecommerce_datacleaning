# spark_ecommerce_datacleaning
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
