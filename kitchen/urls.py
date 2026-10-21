from django.urls import path

from kitchen import views

app_name = 'kitchen'

urlpatterns = [
    path('recipes/', views.KitchenRecipeListView.as_view(), name='recipes'),
    path('recipes/<int:pk>/image/', views.KitchenRecipeImageView.as_view(), name='recipe-image'),
    path('foods/', views.KitchenFoodListView.as_view(), name='foods'),
    path('foods/to-sort/', views.KitchenToSortView.as_view(), name='foods-to-sort'),
    path('foods/names/', views.KitchenFoodNamesView.as_view(), name='foods-names'),
    path('foods/match/', views.KitchenFoodMatchView.as_view(), name='foods-match'),
    path('foods/<int:pk>/move/', views.KitchenFoodMoveView.as_view(), name='food-move'),
    path('foods/<int:pk>/aisle/', views.KitchenFoodAisleView.as_view(), name='food-aisle'),
    path('foods/<int:pk>/keep-name/', views.KitchenFoodKeepNameView.as_view(), name='food-keep-name'),
    path('foods/<int:pk>/delete/', views.KitchenFoodDeleteView.as_view(), name='food-delete'),
    path('foods/<int:pk>/family/', views.KitchenFoodFamilyView.as_view(), name='food-family'),
    path('parse/', views.KitchenParseView.as_view(), name='parse'),
    path('aisles/', views.KitchenAislesView.as_view(), name='aisles'),
    path('duplicates/', views.KitchenDuplicatesView.as_view(), name='duplicates'),
    path('duplicates/dismiss/', views.KitchenDuplicateDismissView.as_view(), name='duplicates-dismiss'),
]
