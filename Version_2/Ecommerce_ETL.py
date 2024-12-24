from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql import SparkSession
import os 
import glob
import shutil

# Download csv and get filenames
os.system("kaggle datasets download oleksiimartusiuk/e-commerce-data-shein --unzip -p ./input_data")
filenames = os.listdir('./input_data/')
print(f"CSV Files Downloaded:\n{filenames}")
# Spark session
spark = SparkSession.builder.master("spark://spark-master:7077").appName("Ecommerce_ETL").getOrCreate() #

# Read data and add category base on file name
def get_category_from_filepath(filepath:str) -> str:
    """
    categoryname is inside filepath
    """
    start_index = filepath.rfind('shein-') + 6
    for i,c in enumerate(filepath):
        if c.isdigit():
            end_index = i - 1
            break
    return filepath[start_index:end_index]  

product_df = None
for f in filenames:
    filepath = f'./input_data/{f}'
    category = get_category_from_filepath(filepath)
    print("Reading file: " + filepath)
    print("Category: " + category)
    df = spark.read.option('header',True).csv(filepath).withColumn('category',lit(category))
    if product_df:
        product_df = product_df.unionByName(df,allowMissingColumns=True)
    else:
        product_df = df

product_df.cache()

#Renaming Columns
columns_renaming = {
    'goods-title-link': 'product_name',
    'goods-title-link--jump href': 'product_href',
    'rank-title':'subcategory_rank',
    'rank-sub':'subcategory',
    'price':'price_usd',
    'discount':'discount_proportion',
    'selling_proposition':'recent_low_estimated_qty_sold',
    'color-count':'color_count',
    'blackfridaybelts-content': 'black_friday_off_usd',
    # Below columns to drop later
    'goods-title-link--jump': 'product_name_jump',
    'blackfridaybelts-bg src': 'black_friday_image',
    'product-locatelabels-img src': 'product_image'
    }

transformed_product_df = product_df
for old_name,new_name in columns_renaming.items():
    transformed_product_df = transformed_product_df.withColumnRenamed(old_name,new_name)

#Cleaning Data
    # E.g.: '-43%' -> 0.43,   'hat' -> NA
def fn_clean_discount(s:str) -> float:
    if not s: 
        # NA value
        return s
    s = s.strip()
    if s[0] == '-' and s[-1] == '%':
        return float(s[1:-1])/100
    else:
        return None
fn_clean_discount = udf(fn_clean_discount,FloatType())

    # E.g.: 'Save $5.74 -> 5.74',     'Sneakers'  -> 0
def fn_clean_black_friday_off_usd(s:str) -> float:
    if not s: 
        # NA value
        return s
    elif True not in [c.isnumeric() for c in s]:
        # There are no numbers inside
        return 0
    else:
        return float(s[s.find('$')+1:])

fn_clean_black_friday_off_usd = udf(fn_clean_black_friday_off_usd,FloatType())        

    # E.g.: 1.4k+ sold recently -> 1400,      800+ sold recently -> 800,       ' Room Decor' -> NA
def fn_clean_recent_low_estimated_qty_sold(s:str)->int:
    if not s: #NA value
        return s
    for i,c in enumerate(s):
        if c.isnumeric():
            l_index = i
            break
    try:
        r_index = s.index('+') - 1
        if s[r_index] == 'k':
            return int(float(s[l_index:r_index])*1000)
        elif s[r_index].isnumeric():
            return int(s[l_index:r_index + 1])
        else:
            raise Exception("last character is not a digit, nor is it a 'k'")
    except: # There are some input values like 'Room Decor' which gives no information. Replace with NA
        return None   

fn_clean_recent_low_estimated_qty_sold = udf(fn_clean_recent_low_estimated_qty_sold,IntegerType())

    # E.g. 'In Lip Care' -> 'Lip Care'
def fn_clean_subcategory(s:str)->str:
    if not s: #NA value
        return s
    elif s[:3] == 'In ' or s[:3] == 'in ': 
        return s[3:].strip().title()
    else:
        return None
fn_clean_subcategory = udf(fn_clean_subcategory,StringType())

    #E.g. #10 Best Sellers -> 10 ,  'Outdoor' -> NA
def fn_clean_subcategory_rank(s:str) -> int:
    if not s: #NA value
        return s
    try:
        return int(s[s.index('#')+1: s.index(' Best')])
    except:
        return None
fn_clean_subcategory_rank = udf(fn_clean_subcategory_rank, IntegerType())

    #E.g. $1,454.07 -> 1454.07,     'Easy To Clean' -> NA
def fn_clean_price_usd(s:str) -> float:
    if not s: #NA
        return s
    dollar_index = s.find('$')
    if dollar_index == -1:
        return None
    else:
        return float(s[s.index('$')+1:].replace(',',''))
fn_clean_price_usd = udf(fn_clean_price_usd,FloatType())

df = transformed_product_df.withColumns({
    'discount_proportion': fn_clean_discount(col('discount_proportion')),
    'black_friday_off_usd': fn_clean_black_friday_off_usd(col('black_friday_off_usd')),
    'recent_low_estimated_qty_sold': fn_clean_recent_low_estimated_qty_sold(col('recent_low_estimated_qty_sold')),
    'subcategory':fn_clean_subcategory(col('subcategory')),
    'subcategory_rank': fn_clean_subcategory_rank(col('subcategory_rank')),
    'price_usd': round(fn_clean_price_usd(col('price_usd')),2)
})


    #Filling NA

        # Changes made below. Irl, we will need to ask the scraper or data source if these assumptions are valid.

        # discount_proportion: Assumes NA value indicates no discount. 

        # black_friday_off_usd: Assumes NA value indicates no black friday off.

        # Color count: Assume NA value indicate only 1 color.

df = df.fillna({
    'discount_proportion': 0,
    'black_friday_off_usd': 0,
    'color_count':1
})

    #product_name and product_name_jump has the same information, with product_name having far less NA.
df = df.withColumn('product_name',coalesce('product_name','product_name_jump'))


    # Dropping Redundant Columns

df = df.select('product_name','price_usd','discount_proportion','black_friday_off_usd','category','subcategory','subcategory_rank','recent_low_estimated_qty_sold','color_count')


# Dealing with duplicates

    # Inspecting duplicates
        #df.count() # 82121
        #df.dropDuplicates().count() #79202
        #df.dropDuplicates(['product_name']).count() #71483

df.cache()    

df.dropDuplicates().createOrReplaceTempView('x')
h = spark.sql("""
          with duplicates as (
              select product_name,count(*) as cnt
              from x
              group by product_name
              having cnt >= 2
          )
          select *
          from x
          where product_name in (select product_name from duplicates)
          order by product_name
          """)
h.cache() 
h.show()

# It is difficult to know how duplicate **product_name** should be dealt with. It depends the data source. So, we need more information. But here are some notes from looking at the table created for duplicate **product_name**:
# 
# 1. Duplicates may have different **price_usd**, **discount_proportion**, **black_friday_off_usd**, **subcategory**, **subcategory_rank**, **recent_low_estimated_qty_sold**, and **category** 
# 
# 2. Possible solution:
# * We can group by product_name and fill NAs of the columns above using mean or mode. Then we drop duplicate rows (using all columns)


h.createOrReplaceTempView('temp_view_duplicates')
df.createOrReplaceTempView('original_df')

df_filled = spark.sql("""
               with aggregated_values as (
                   select 
                    product_name,
                    median(price_usd) as price_usd,
                    median(discount_proportion) as discount_proportion,
                    median(black_friday_off_usd) as black_friday_off_usd,
                    mode(subcategory) as subcategory,
                    round(median(subcategory_rank)) as subcategory_rank,
                    median(recent_low_estimated_qty_sold) as recent_low_estimated_qty_sold
                   from temp_view_duplicates
                   group by product_name
               )
               select
               o.product_name,
               coalesce(o.price_usd,a.price_usd) as price_usd,
               coalesce(o.discount_proportion,a.discount_proportion) as discount_proportion,
               coalesce(o.black_friday_off_usd,a.black_friday_off_usd) as black_friday_off_usd,
               category,
               coalesce(o.subcategory,a.subcategory) as subcategory,
               coalesce(o.subcategory_rank,a.subcategory_rank) as subcategory_rank,
               coalesce(o.recent_low_estimated_qty_sold,a.recent_low_estimated_qty_sold) as recent_low_estimated_qty_sold,
               color_count

               from original_df o left join aggregated_values a on o.product_name = a.product_name
               """)


df_filled = df_filled.dropDuplicates()
df_filled.cache()
df_filled.count() #79,008
product_df.unpersist()
df.unpersist()
h.unpersist()


# More work needs to be done in the future as we still have duplicate **product_name**. We will need to get more information before we can know how to proceed.

# # Feature Engineering

# We will create a new column for net price using the formula below:
# 
# net_price = price_usd * (1-discount_proportion) - black_friday_off_usd
# 
# In real life, we will need to check whether the black friday discount or the discount proportion should be applied first.
# 


df_filled_fe = df_filled.withColumn(
  'net_price_usd',
  col('price_usd') * (1 - col('discount_proportion')) - col('black_friday_off_usd')
)


# Output Data

    # Changing data type
df_filled_fe_casted = df_filled_fe.withColumns({
    'subcategory_rank': col('subcategory_rank').cast('Integer'),
    'recent_low_estimated_qty_sold': col('recent_low_estimated_qty_sold').cast('Integer'),
    'color_count':col('color_count').cast('Integer')
})

df_filled_fe_casted.show() 

# Output to CSV
print("Writing to csv")
df_filled_fe_casted.coalesce(1).write.mode('overwrite').option('header', True).csv("./output_data/testing.csv") #testing.csv is actually a folder, not a csv
# Rename the file
print("Renaming file")
output_file = glob.glob(f"./output_data/testing.csv/part-00000-*.csv")[0]
os.rename(output_file, "output_data/output_cleaned_e_commerce_data.csv")
# Delete the testing.csv folder
shutil.rmtree('./output_data/testing.csv')