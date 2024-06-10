from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse, JsonResponse
import os
import boto3
import io
from uuid import uuid4 # For generating unique filenames
from django.conf import settings
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import json
from botocore.exceptions import ClientError
import requests
import jwt
from jwt.algorithms import RSAAlgorithm
import json
from functools import wraps
from . import util
from zipfile import ZipFile
import base64

'''Notes: 
update env variables
create a decorator for login function
create db to store client details
use access token for login instead of id token
'''

image_details = {
    'image_dimensions': '1024 x 772',
    'model_name': 'm1',
    'model_upload_date': '2024-05-06',
    'model_type': 'stardist'
}

@api_view(['GET'])
def test(requests):
    print("all_system_go")
    return HttpResponse("working")

@api_view(['GET'])
def check_auth(requests):
    token_check = util.jwt_required(requests)
    if token_check==True:
        data = requests.data
        return Response("auth_working")
    return Response(json.dumps({"400":"token error","error":str(token_check)}))

# @api_view(['GET'])
# def folder_contents(requests):
#     data = requests.data
#     print(data)
#     s3 = boto3.client('s3', aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)
#     folder_contents = util.get_s3_folder_contents_as_string(s3, settings.BUCKET_NAME, data['folder_name'])
#     return Response(folder_contents)   

@api_view(['GET'])
def folder_contents(requests):
    data = requests.data
    data = requests.query_params.get('folder_name')
    print(data)
    s3 = boto3.client('s3', aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)
    folder_contents = util.get_s3_folder_contents_as_string(s3, settings.BUCKET_NAME, data)
    return Response(folder_contents)    

@api_view(['POST'])
def create_client(requests):
    token_check = util.jwt_required(requests)
    if token_check==True:

        data = (requests.data)
        folder_name = data['client_name']
        bucket_name = settings.BUCKET_NAME
        # Initialize a session using Amazon S3
        s3 = boto3.client('s3', aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)
        # The key for a "folder" ends with a '/'
        folder_key = f'{folder_name}/'
        try:
            # Create the folder by putting a zero-byte object with a folder key
            s3.put_object(Bucket=bucket_name,Body='', Key=folder_key)
            print(f'Folder "{folder_name}" created successfully in bucket "{bucket_name}".')
            return Response ("{'success 200':'client created succesfully'}")
        except NoCredentialsError:
            print('Credentials not available.')
            return Response ("{'error 500':'Credentials not available.'}")
        except PartialCredentialsError:
            print('Incomplete credentials provided.')
            return Response ("{'error 500':'Credentials not available.'}")
        
    return Response(json.dumps({"400":"token error","error":str(token_check)}))
    
@api_view(['POST'])
def create_project(requests):
    token_check = util.jwt_required(requests)
    if token_check==True:

        data = (requests.data)
        folder_name = data['client_name']
        project_name = data['project_name']
        bucket_name = settings.BUCKET_NAME

        # Initialize a session using Amazon S3
        s3 = boto3.client('s3', aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)
        # The key for a "folder" ends with a '/'
        folder_key = f'{folder_name}/{project_name}/'
        try:
            # Create the folder by putting a zero-byte object with a folder key
            s3.put_object(Bucket=bucket_name,Body='', Key=folder_key)
            print(f'Project "{project_name}" created successfully in bucket "{bucket_name}".')
            return Response ("{'success 200':'Project created succesfully'}")
        
        except NoCredentialsError:
            print('Credentials not available.')
            return Response ("{'error 500':'Credentials not available.'}")
        
        except PartialCredentialsError:
            print('Incomplete credentials provided.')
            return Response ("{'error 500':'Credentials not available.'}")
        
    return Response(json.dumps({"400":"token error","error":str(token_check)}))
    
@api_view(['POST'])
def create_model(requests):
    token_check = util.jwt_required(requests)
    if token_check==True:

        client_name = requests.POST.get('client_name')
        project_name = requests.POST.get('project_name')
        model_name = requests.POST.get('model_name')
        bucket_name = settings.BUCKET_NAME

        model_file = requests.FILES.get('model_file')
        print(model_file.name)

        # Initialize a session using Amazon S3
        s3 = boto3.client('s3', aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)
        # The key for a "folder" ends with a '/'
        folder_key = f'{client_name}/{project_name}/{model_name}/'
        input_folder_key = f'{folder_key}input_folder/'
        output_folder_key = f'{folder_key}output_folder/'
        model_folder_key = f'{folder_key}model_folder/'
        model_file_key = f'{model_folder_key}{model_file.name}'
        try:
            # Create the folder by putting a zero-byte object with a folder key
            s3.put_object(Bucket=bucket_name,Body='', Key=folder_key)
            s3.put_object(Bucket=bucket_name,Body='', Key=input_folder_key)
            s3.put_object(Bucket=bucket_name,Body='', Key=output_folder_key)
            s3.put_object(Bucket=bucket_name,Body='', Key=model_folder_key)
            s3.upload_fileobj(model_file, bucket_name, model_file_key)
            print(f'Model "{model_name}" created successfully in bucket "{bucket_name}".')
            return Response ("{'success 200':'Model created succesfully'}")
        
        except NoCredentialsError:
            print('Credentials not available.')
            return Response ("{'error 500':'Credentials not available.'}")
        
        except PartialCredentialsError:
            print('Incomplete credentials provided.')
            return Response ("{'error 500':'Credentials not available.'}")
        
    return Response(json.dumps({"400":"token error","error":str(token_check)}))
    
@api_view(['POST'])
def login(requests):
    cognito_client = boto3.client('cognito-idp',aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)  # Use your region
    data = requests.data
    username = data['username']
    password = data['password']
    access_token = util.authenticate_user(cognito_client, username, password)
    # decoded_token = util.verify_jwt_token(access_token, settings.USER_POOL_ID, settings.COG_CLIENT_ID, settings.REGION_NAME)
    # print(decoded_token)
    # username = decoded_token.get('cognito:username') or decoded_token.get('sub')
    if access_token !="":
        print("Access Token:", access_token)
        return Response(access_token)
    else:
        return Response("error check password")

@api_view(['POST'])
def upload_image(requests):
    
    token_check = util.jwt_required(requests)
    if token_check==True:

        client_name = requests.POST.get('client_name')
        project_name = requests.POST.get('project_name')
        model_name = requests.POST.get('model_name')
        bucket_name = settings.BUCKET_NAME
        image = requests.FILES.get('image')

        # Initialize a session using Amazon S3
        s3_client = boto3.client('s3', aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)
        
        uuid = uuid4()  # for unique filename
        uuid = str(uuid).replace('-', '')
        print(uuid)
        
        # The key for a "folder" ends with a '/'
        folder_key = f"{client_name}/{project_name}/{model_name}/"
        input_file_name = f"{folder_key}input_folder/{client_name}-{project_name}-{model_name}-mymodel_Dec13_keras_new_dataset.keras-input_folder-output_folder-{uuid}-.{image.name.split('.')[-1]}"
        output_file_name = f"{folder_key}output_folder/processed_image_{client_name}-{project_name}-{model_name}-mymodel_Dec13_keras_new_dataset.keras-input_folder-output_folder-{uuid}-.{image.name.split('.')[-1]}"
        try:
            # Create the folder by putting a zero-byte object with a folder key
            # s3_client.put_object(Bucket=bucket_name,Body='', Key=folder_key)
            # print(f'Model "{model_name}" created successfully in bucket "{bucket_name}".')
            util.save_input_into_bucket(s3_client, bucket_name, image, input_file_name)
            print(f'file uploaded to {input_file_name}')
            base64_output_image = util.fetch_output_from_bucket(settings.CLOUDFRONT_URL, output_file_name)
            response = {"image": base64_output_image}
            return JsonResponse(response)
        
        except NoCredentialsError:
            print('Credentials not available.')
            return Response ("{'error 500':'Credentials not available.'}")
        
        except PartialCredentialsError:
            print('Incomplete credentials provided.')
            return Response ("{'error 500':'Credentials not available.'}")
        
    return Response(json.dumps({"400":"token error","error":str(token_check)}))
        
@api_view(['POST'])
def upload_zip(requests):

    token_check = util.jwt_required(requests)
    if token_check==True:

        client_name = requests.POST.get('client_name')
        project_name = requests.POST.get('project_name')
        model_name = requests.POST.get('model_name')
        bucket_name = settings.BUCKET_NAME
        zip_file = requests.FILES.get('zip_file')

        if zip_file and zip_file.name.endswith('.zip'):
            uuid = str(uuid4())
            file_name = zip_file.name
            saved_file_path = os.path.join('temp_files', uuid)

            if not os.path.exists(saved_file_path):
                os.makedirs(saved_file_path)

            zip_file_path = os.path.join(saved_file_path, file_name)
            # zip_file.save(zip_file_path)
            # above method was not working as Django's InMemoryUploadedFile object does not have a save method

            with open(zip_file_path, 'wb+') as destination:
                for chunk in zip_file.chunks():
                    destination.write(chunk)

            with ZipFile(zip_file_path, 'r') as zip:
                zip.extractall(saved_file_path)

            input_images_path = os.path.join(saved_file_path, file_name.split('.')[0])
            processed_images = {}
            original_images = {}

            # Initialize a session using Amazon S3
            s3_client = boto3.client('s3', aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)
            # The key for a "folder" ends with a '/'
            folder_key = f'{client_name}/{project_name}/{model_name}/'
            try:
                # Create the folder by putting a zero-byte object with a folder key

                for filename in os.listdir(input_images_path):
                    file_path = os.path.join(input_images_path, filename)
                    with open(file_path, 'rb') as f:
                        filename_for_s3_input = folder_key + 'input_folder/' + client_name + '-' + project_name + '-' + model_name + '-mymodel_Dec13_keras_new_dataset.keras-input_folder-output_folder-' + uuid + '-.' + filename.split('.')[-1]
                        util.save_input_into_bucket(s3_client, bucket_name=bucket_name, image_file=f, filename=filename_for_s3_input)
                    filename_for_s3_output = folder_key + 'output_folder/processed_image_' + client_name + '-' + project_name + '-' + model_name + '-mymodel_Dec13_keras_new_dataset.keras-input_folder-output_folder-' + uuid + '-.' + filename.split('.')[-1]
                    processed_image_base64 = util.fetch_output_from_bucket(settings.CLOUDFRONT_URL, filename_for_s3_output)
                    processed_images[filename.split('.')[0]] = processed_image_base64
                    original_images[filename.split('.')[0]] = base64.b64encode(open(file_path, 'rb').read()).decode('utf-8')

                print(f'Model "{model_name}" created successfully in bucket "{bucket_name}".')
                response = {"processed_images": processed_images, "original_images": original_images, "image_details": image_details}
                return JsonResponse(response)
                # return Response ("{'success 200':'Model created succesfully'}")
            
            except NoCredentialsError:
                print('Credentials not available.')
                return Response ("{'error 500':'Credentials not available.'}")
            
            except PartialCredentialsError:
                print('Incomplete credentials provided.')
                return Response ("{'error 500':'Credentials not available.'}")
        else:
            return Response("{'error 400':'file not a zip file'}")
    return Response(json.dumps({"400":"token error","error":str(token_check)}))
        

@api_view(['POST'])
def delete_project(requests):
    token_check = util.jwt_required(requests)
    if token_check==True:

        client_name = requests.POST.get('client_name')
        project_name = requests.POST.get('project_name')

        # Initialize a session using Amazon S3
        s3_client = boto3.client('s3', aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)
        
        # Now the folder to be deleted
        folder_key = client_name + '/' + project_name + '/'

        # Get a list of all objects in the folder
        objects_to_delete = s3_client.list_objects(Bucket=settings.BUCKET_NAME, Prefix=folder_key)

        # Delete all objects in the folder
        for object in objects_to_delete.get('Contents', []):
            s3_client.delete_object(Bucket=settings.BUCKET_NAME, Key=object['Key'])

        return Response("{'success 200':'Folder deleted successfully'}")
    
    return Response(json.dumps({"400":"token error","error":str(token_check)}))

@api_view(['GET'])
def get_images(requests):
    data = requests.query_params.get('folder_name')
    print(data)
    # Initialize a session using Amazon S3
    s3_client = boto3.client('s3', aws_access_key_id=settings.ACCESS_KEY, aws_secret_access_key=settings.KEY_AWS, region_name=settings.REGION_NAME)
    folder_contents =  util.get_s3_folder_contents_as_string(s3_client, settings.BUCKET_NAME, data)
    try:
        filtered_images = [file for file in folder_contents if file.lower().endswith(('.jpg', '.png'))]
        if (filtered_images==""):
            return Response("error recieved no images in the said folder")
    except Exception as error:
        return Response(error,"error recieved no images in the said folder")
    base64_images = {}
    # Get base64 encoding for each image
    for image_key in filtered_images:
        base64_images[image_key] = util.get_image_as_base64(s3_client, settings.BUCKET_NAME, image_key)
    
    
    # return base64_images
    return JsonResponse(base64_images)
