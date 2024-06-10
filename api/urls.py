from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path("test", views.test),
    path("create-client", views.create_client),
    path("create-project", views.create_project),
    path("create-model", views.create_model),
    path("contents", views.folder_contents),
    path("login", views.login),
    path("check-auth", views.check_auth),
    path("upload-image", views.upload_image),
    path("upload-zip", views.upload_zip),
    path("delete-project", views.delete_project),
    path("get-images", views.get_images),
]
