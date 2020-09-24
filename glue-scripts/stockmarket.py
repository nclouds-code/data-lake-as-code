# Imports:
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext, DynamicFrame
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.types import *

args = getResolvedOptions(sys.argv,
        [
            "context",
            "tempbucket",
            "database",
            "tablename",
            "redshifturl",
            "iamrole"
        ]
    )

# Context:
# For notebook work, uncomment `context = "notebook"` and comment `context = args["context"]`
# context = "notebook"
context = args["context"]

if context == "notebook":
    tempbucket = "s3://bucket/temp-directory/"
    Pdatabase = "poc-stockmarket"
    Ptablename = "datalake_stockmarket_partitioned"
    Predshifturl = "jdbc:redshift://datalake-poc-v3.e1275e563a9f.us-east-1.redshift.amazonaws.com:5439/dev?user=root&password=strongpass"
    Piamrole = "arn:aws:iam::<account-number>:role/poc-stockmarket-role"
    # For Zeppelin notebook use these:
    glueContext = GlueContext(SparkContext.getOrCreate())
else:
    tempbucket = args["tempbucket"]
    Pdatabase = args["database"]
    Ptablename = args["tablename"]
    Ptablename = Ptablename.replace("-","_")
    Predshifturl = args["redshifturl"]
    Piamrole = args["iamrole"]
    # For Glue Job use these:
    sc = SparkContext()
    glueContext = GlueContext(sc)

spark = glueContext.spark_session
job = Job(glueContext)

spark.conf.set("spark.sql.sources.partitionOverwriteMode","dynamic")

# Load Data:
# Source dynamic frame from glue catalog
stockmarketDynamicFarme = glueContext.create_dynamic_frame.from_catalog(database=Pdatabase, table_name=Ptablename)

# Select all data
stockmarketDynamicFarme.toDF().registerTempTable("stockmarket")
stockmarket_results = spark.sql("SELECT * FROM stockmarket")

# Transform data:
stockmarket_results = stockmarket_results.withColumn("ticker_type", stockmarket_results["partition_0"])
stockmarket_results = stockmarket_results.withColumn("ticker", stockmarket_results["partition_1"])
stockmarket_results = stockmarket_results.withColumnRenamed("date","date_1")
stockmarket_results = stockmarket_results.withColumnRenamed("open","open_1")
stockmarket_results = stockmarket_results.drop("partition_0")
stockmarket_results = stockmarket_results.drop("partition_1")
stockmarket_results = stockmarket_results.withColumn("date", stockmarket_results["date"].cast(DateType()))

# Write data to Redshift:
stockmarket_results.write.partitionBy("ticker","ticker_type").format("com.databricks.spark.redshift") \
    .option("url", Predshifturl) \
    .option("dbtable", "stockmarket") \
    .option("tempdir", tempbucket) \
    .option("aws_iam_role", Piamrole) \
  .mode("error") \
  .save()
