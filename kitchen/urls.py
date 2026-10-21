from django.urls import path

from kitchen import views

app_name = 'kitchen'

urlpatterns = [
    path('recipes/', views.KitchenRecipeListView.as_view(), name='recipes'),
]
