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



class CachedLink:
    def __init__(self, link, created):
        self.link = link
        self.created = created

class LinkCache:
    def __init__(self, link_duration, bucket=None, sec_buffer=15):
        self.link_duration = link_duration
        self.bucket = bucket
        self.sec_buffer = sec_buffer

        self.cache = {}

    def add_link(self, image_name):
        if self.bucket:
            link = s3_client.generate_presigned_url("get_object", Params={"Bucket" : self.bucket, "Key" : image_name}, ExpiresIn=self.link_duration)
        self.cache[image_name] = CachedLink(link, datetime.datetime.now(tz=datetime.timezone.utc))
        return link

    def get_link(self, image_name):
        try:
            link_item = self.cache[image_name]
            if self.check_timedelta(link_item.created):
                return link_item.link
            else:
                self.validate_cache()
                return self.add_link(image_name)

        except KeyError:
            self.validate_cache()
            return self.add_link(image_name)


    def check_timedelta(self, created):
        current_time = datetime.datetime.now(tz=datetime.timezone.utc)
        expires_by = created + datetime.timedelta(seconds=(self.link_duration - self.sec_buffer))
        if current_time < expires_by:
            return True
        else:
            return False


    def validate_cache(self):
        remove_names = []
        for image_name, link_item in self.cache.items():
            if not self.check_timedelta(link_item.created):
                remove_names.append(image_name)
        for name in remove_names:
            del self.cache[name]
    


s3_client = boto3.client("s3",
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET,
    config=Config(region_name=AWS_REGION, signature_version = AWS_SIGVERSION))


mongo_uri = f"mongodb+srv://{MONGO_USER}:{MONGO_PW}@gifcluster.hdfhgyq.mongodb.net/?retryWrites=true&w=majority"

mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))



post_db = mongo_client.gifcluster.posts
user_db = mongo_client.gifcluster.users

app = Flask(__name__)

post_cache = LinkCache(100, AWS_GIFBUCKET)
user_cache = LinkCache(100, AWS_USERBUCKET)

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
                },
                "like_count" : {
                    "$size" : "$likes"
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
                "like_count" : 1,
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



    post_url = post_cache.get_link(post_data["image_name"])


    picture_url = user_cache.get_link(post_data["picture_name"])

    post_data["post_url"] = post_url

    post_data["picture_url"] = picture_url


    return jsonify(post_data)

@app.route("/feed/<last_id>")
def get_feed(last_id):
    session_user_id = 1



    user_record = user_db.find_one({"user_id" : session_user_id})

    last_id = int(last_id)
    if last_id == 0:
        match = {
            "$expr" : {"$in" : ["$user_id", user_record["circles"]]},


            }
    else:
        date = post_db.find_one({"post_id" : last_id})["date"]
        print(date)
        match = {
                "$expr" : {"$in" : ["$user_id", user_record["circles"]]},
                "$expr" : {"$lt" : ["$date", date]}
            }
    


    pipeline = [

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
            "$match" : match
        },



        {
            "$sort" : {
                "date" : -1
            }
        },
        {
            "$limit" : 10
        },



        {
            "$addFields" : {
                "comment_count" : {
                    "$size" : "$comments"
                },
                "user_liked" : {
                    "$in" : [session_user_id, "$likes"]
                },
                "like_count" : {
                    "$size" : "$likes"
                },

                    # "last_post" : "$last_post"

            },

        },
        {
            "$project" : {
                # "last_post" : 1,
                "post_id" : 1,
                "user_id" : 1,
                "width" : 1,
                "height" : 1,
                "image_name" : 1,
                "title" : 1,
                "caption" : 1,
                "tags" : 1,
                "comment_count" : 1,
                "like_count" : 1,
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

    post_data = list(post_db.aggregate(pipeline))



    post_url = post_cache.get_link(post_data["image_name"])


    picture_url = user_cache.get_link(post_data["picture_name"])

    post_data["post_url"] = post_url

    post_data["picture_url"] = picture_url


    return jsonify(post_data)

if __name__ == "__main__":

    app.run(host="127.0.0.1", port=8000)
