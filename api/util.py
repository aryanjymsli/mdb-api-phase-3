from django.conf import settings
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import json
from botocore.exceptions import ClientError
import requests
import jwt
from jwt.algorithms import RSAAlgorithm
import json
from functools import wraps
import base64
import time

# get_s3_folder_contents_as_string
def get_s3_folder_contents_as_string(s3_client, bucket_name, folder_name):
    try:
        # List objects within the specified folder
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_name)
        
        if 'Contents' not in response:
            print(f"No contents found in folder '{folder_name}'")
            return ""

        # Initialize an empty string to accumulate the contents
        folder_contents = ""
        keys=[]

        # Iterate through each object in the folder
        for obj in response['Contents']:
            key = obj['Key']
            keys.append(key)
            
            print(f"Reading object: {key}")
            # responsess = s3_client.get_object(Bucket=bucket_name, Key=folder_name)
            # # Get the object
            # obj_response = s3_client.get_object(Bucket=bucket_name, Key=key)

            # # Read the object content and decode it to a string
            # content = obj_response['Body'].read().decode('utf-8')
            # folder_contents += key + "\n"
        folder_contents=keys

        return folder_contents
    except Exception as e:
        print("Unexpected error:", e)
    return ""

"""function to authenticate user using emil and password 
function to authenticate user using emil and password 
returns JWT toke from cognito
"""
def authenticate_user(client, username, password):
    try:
        response = client.initiate_auth(
            ClientId=settings.COG_CLIENT_ID,  # Replace with your App Client ID
            AuthFlow=settings.COD_AUTH_FLOW,
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        print("Authentication successful:", response)
        # we can also have AccessToken here
        return response['AuthenticationResult']['IdToken']
    except ClientError as e:
        print("Error during authentication:", e)

# Function to get JWKS keys from Cognito
def get_jwks_keys(user_pool_id, region):
    jwks_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
    response = requests.get(jwks_url)
    response.raise_for_status()
    return response.json()['keys']

#verify JWT token
def verify_jwt_token(token, user_pool_id, app_client_id, region):
    jwks_keys = get_jwks_keys(user_pool_id, region)
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header['kid']
    print(kid,"kid")
    public_key = None
    for key in jwks_keys:
        print(key)
        if key['kid'] == kid:
            public_key = RSAAlgorithm.from_jwk(json.dumps(key))
            break
    if public_key is None:
        raise ValueError('Public key not found in JWKS')
    try:
        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=app_client_id
        )
        return decoded_token
    
    except jwt.ExpiredSignatureError:
        raise ValueError('Token has expired')
    except jwt.InvalidTokenError as e:
        raise ValueError(f'Token is invalid: {e}')
    except Exception as e:
        print(f"Token verification error: {e}")

# JWT verifier decorator
def jwt_required(requests):
        token = None
        if 'Authorization' in requests.headers:
            token = requests.headers['Authorization'].split(" ")[0]
        if not token:
            return json.dumps({'message': 'Token is missing'}), 401

        try:
            verify_jwt_token(token, settings.USER_POOL_ID, settings.COG_CLIENT_ID, settings.REGION_NAME)
        except Exception as e:
            print(e)
            return e
        return True

def save_input_into_bucket(s3_client, bucket_name, image_file, filename):
    s3_client.upload_fileobj(image_file, bucket_name, filename)

def fetch_output_from_bucket(cloudfront_url, filename):
    url = cloudfront_url + filename
    # url = 'https://d29aptxyntziir.cloudfront.net/YMC/FMS/Models/output_folder/processed_image_YMC-FMS-Models-mymodel_Dec13_keras_new_dataset.keras-input_folder-output_folder-2fcc01a35deb469e91cbf5f482eb72f0-.jpg'
    print(url)

    # Try to fetch image 30 times
    for _ in range(50):
        try:
            response = requests.get(url, verify=False)
            print(response.status_code)
            response.raise_for_status()
            base64_content = base64.b64encode(response.content).decode('utf-8')
            print(base64_content)
            return base64_content
        except:
            time.sleep(2)
    raise Exception()

def get_image_as_base64(s3,bucket_name, image_key):
    # Get the image from S3
    response = s3.get_object(Bucket=bucket_name, Key=image_key)
    
    # Read the image content
    image_content = response['Body'].read()
    
    # Encode the image content to base64
    base64_encoded = base64.b64encode(image_content).decode('utf-8')
    return base64_encoded