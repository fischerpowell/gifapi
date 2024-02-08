from flask import Flask, jsonify, render_template
import os
from dotenv import load_dotenv
import boto3
from botocore.client import Config
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import datetime


load_dotenv()

AWS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.environ.get("AWS_ACCESS_KEY_SECRET")
AWS_REGION = os.environ.get("AWS_REGION")
AWS_SIGVERSION = os.environ.get("AWS_SIGVERSION")
AWS_GIFBUCKET = os.environ.get("AWS_GIFBUCKET")
AWS_USERBUCKET = os.environ.get("AWS_USERBUCKET")
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PW = os.environ.get("MONGO_PW")

s3_client = boto3.client("s3",
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET,
    config=Config(region_name=AWS_REGION, signature_version = AWS_SIGVERSION))


mongo_uri = f"mongodb+srv://{MONGO_USER}:{MONGO_PW}@gifcluster.hdfhgyq.mongodb.net/?retryWrites=true&w=majority"

mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))



post_db = mongo_client.gifcluster.posts
user_db = mongo_client.gifcluster.users

app = Flask(__name__)


@app.route('/')
def main_index():
    return 'Hi Jake'


@app.route("/post/<post_id>")
def get_post(post_id):
    session_user_id = 1

    post_id = int(post_id)

    pipeline = [
        {
            "$match" : {
                "post_id" : post_id
            }
        },
        {
            "$lookup" : {
                "from" : "users",
                "localField" : "user_id",
                "foreignField" : "user_id",
                "as" : "user_record",
            }
        },
        {
            "$unwind" : "$user_record"
        },
        {
            "$addFields" : {
                "comment_count" : {
                    "$size" : "$comments"
                },
                "user_liked" : {
                    "$in" : [session_user_id, "$likes"]
                }
            },

        },
        {
            "$project" : {
                "post_id" : 1,
                "user_id" : 1,
                "width" : 1,
                "height" : 1,
                "image_name" : 1,
                "title" : 1,
                "caption" : 1,
                "tags" : 1,
                "comment_count" : 1,
                "user_liked" : 1,
                "name_color" : "$user_record.name_color",
                "username" : "$user_record.username",
                "picture_name" : "$user_record.picture_name",
                "date" : 1,
                "circle" : 1,
                "_id" : 0,

            }
        },

    ]

    post_data = list(post_db.aggregate(pipeline))[0]



    post_url = s3_client.generate_presigned_url("get_object", Params={"Bucket" : AWS_GIFBUCKET, "Key" : post_data["image_name"]}, ExpiresIn=100)


    picture_url = s3_client.generate_presigned_url("get_object", Params={"Bucket" : AWS_USERBUCKET, "Key" : post_data["picture_name"]}, ExpiresIn=100)

    post_data["post_url"] = post_url

    post_data["picture_url"] = picture_url


    return jsonify(post_data)

if __name__ == "__main__":

    app.run(host="127.0.0.1", port=8000)
