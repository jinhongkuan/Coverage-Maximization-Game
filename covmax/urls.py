"""covmax URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from game.models import start_timer
from game.views import game_view, board_view, main_view, admin_view, admin_observation_view, graph_view, end_round_view 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', main_view, name='home'),
    path('game', game_view, name='game'),
    path('board', board_view, name='board'),
    path('admin', admin_view, name='admin'),
    path('adminview', admin_observation_view, name='observation'),
    path('graph', graph_view, name='graph'),
    path('end_round', end_round_view, name='end round')
]

start_timer()