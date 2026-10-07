from django.urls import path

from . import views

app_name = "quizzes"

urlpatterns = [
    path("", views.quiz_list, name="quiz_list"),
    path("<int:pk>/", views.quiz_detail, name="quiz_detail"),
    path("<int:pk>/take/", views.quiz_take, name="quiz_take"),
    path("attempts/<int:pk>/", views.quiz_result, name="quiz_result"),
]
