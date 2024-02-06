from flask import Flask, jsonify, render_template
import os
from dotenv import load_dotenv
import boto3
from botocore.client import Config

load_dotenv()

AWS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.environ.get("AWS_ACCESS_KEY_SECRET")
AWS_REGION = os.environ.get("AWS_REGION")
AWS_SIGVERSION = os.environ.get("AWS_SIGVERSION")
AWS_GIFBUCKET = os.environ.get("AWS_GIFBUCKET")

app = Flask(__name__)


@app.route('/')
def main_index():
    return 'Hi Jake'


@app.route("/post/<post_id>")
def get_post(post_id):
    s3_client = boto3.client("s3",
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
        config=Config(region_name=AWS_REGION, signature_version = AWS_SIGVERSION))


    post_url = s3_client.generate_presigned_url("get_object", Params={"Bucket" : AWS_GIFBUCKET, "Key" : "test.gif"}, ExpiresIn=100)



    post_data = {
        "post_id" : post_id,
        "post_url" : post_url
    }
    return jsonify(post_data)

if __name__ == "__main__":

    app.run(host="127.0.0.1", port=8000)