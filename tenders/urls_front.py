from django.urls import path
from .views_front import (
    home,
    verification_success,
    tender_detail,
    create_tender,
    edit_tender,
    cancel_tender,
    publish_tender,
    create_application,
    edit_application,
    withdraw_application,
    choose_winner,
    application_documents,
    upload_document,
    delete_document,
    register,
)

urlpatterns = [
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('registration-success/', verification_success, name='verification_success'),

    path('tender/create/', create_tender, name='create_tender'),
    path('tender/<int:tender_id>/', tender_detail, name='tender_detail'),
    path('tender/<int:tender_id>/edit/', edit_tender, name='edit_tender'),
    path('tender/<int:tender_id>/cancel/', cancel_tender, name='cancel_tender'),
    path('tender/<int:tender_id>/publish/', publish_tender, name='publish_tender'),
    path('tender/<int:tender_id>/choose-winner/', choose_winner, name='choose_winner'),

    path('tender/<int:tender_id>/apply/', create_application, name='create_application'),
    path('application/<int:application_id>/edit/', edit_application, name='edit_application'),
    path('application/<int:application_id>/withdraw/', withdraw_application, name='withdraw_application'),

    path('application/<int:application_id>/documents/', application_documents, name='application_documents'),
    path('application/<int:application_id>/documents/upload/', upload_document, name='upload_document'),
    path('document/<int:document_id>/delete/', delete_document, name='delete_document'),
]
