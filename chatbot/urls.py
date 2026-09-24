from django.urls import path
from . import views

urlpatterns = [
    path('mensaje/', views.api_chatbot_mensaje, name='chatbot_mensaje'),
]
