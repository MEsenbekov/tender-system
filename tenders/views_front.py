from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import RegisterForm
from .models import Tender, Application, VerificationRequest, Document
from .services import close_expired_tenders


@login_required
def home(request):
    close_expired_tenders()

    if request.user.role == 'admin':
        tenders = Tender.objects.all().order_by('-created_at')
    elif request.user.role == 'customer':
        tenders = Tender.objects.filter(customer=request.user).order_by('-created_at')
    else:
        tenders = Tender.objects.filter(
            status='published',
            deadline__gt=timezone.now()
        ).order_by('-created_at')

    return render(request, 'home.html', {'tenders': tenders})


def verification_success(request):
    return render(request, 'verification_success.html')


@login_required
def tender_detail(request, tender_id):
    close_expired_tenders()
    tender = get_object_or_404(Tender, id=tender_id)

    user_application = None
    if request.user.role == 'supplier':
        user_application = Application.objects.filter(
            tender=tender,
            supplier=request.user
        ).first()

    applications_count = tender.applications.count()
    can_edit = (request.user == tender.customer or request.user.role == 'admin') and applications_count == 0
    can_cancel = request.user == tender.customer or request.user.role == 'admin'
    can_choose_winner = can_cancel and tender.status == 'closed'

    return render(request, 'tender_detail.html', {
        'tender': tender,
        'user_application': user_application,
        'applications_count': applications_count,
        'can_edit': can_edit,
        'can_cancel': can_cancel,
        'can_choose_winner': can_choose_winner,
    })


@login_required
def create_tender(request):
    if request.user.role not in ['customer', 'admin']:
        messages.error(request, 'У вас нет доступа к созданию тендеров.')
        return redirect('home')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        deadline = request.POST.get('deadline')
        requirements = request.POST.get('requirements')

        if not title or not description or not deadline:
            messages.error(request, 'Заполните обязательные поля.')
            return render(request, 'create_tender.html')

        Tender.objects.create(
            title=title,
            description=description,
            deadline=deadline,
            requirements=requirements,
            customer=request.user,
            status='draft'
        )
        messages.success(request, 'Тендер создан как черновик.')
        return redirect('home')

    return render(request, 'create_tender.html')


@login_required
def edit_tender(request, tender_id):
    tender = get_object_or_404(Tender, id=tender_id)

    if request.user != tender.customer and request.user.role != 'admin':
        return HttpResponseForbidden('Нет доступа.')

    if tender.applications.exists():
        messages.error(request, 'Нельзя редактировать тендер после появления заявок. Можно только отменить.')
        return redirect('tender_detail', tender_id=tender.id)

    if request.method == 'POST':
        tender.title = request.POST.get('title')
        tender.description = request.POST.get('description')
        tender.deadline = request.POST.get('deadline')
        tender.requirements = request.POST.get('requirements')
        tender.save()

        messages.success(request, 'Тендер обновлён.')
        return redirect('tender_detail', tender_id=tender.id)

    return render(request, 'edit_tender.html', {'tender': tender})


@login_required
def cancel_tender(request, tender_id):
    tender = get_object_or_404(Tender, id=tender_id)

    if request.user != tender.customer and request.user.role != 'admin':
        return HttpResponseForbidden('Нет доступа.')

    if request.method == 'POST':
        tender.status = 'cancelled'
        tender.save()
        messages.success(request, 'Тендер отменён.')
        return redirect('tender_detail', tender_id=tender.id)

    return render(request, 'cancel_tender.html', {'tender': tender})


@login_required
def publish_tender(request, tender_id):
    tender = get_object_or_404(Tender, id=tender_id)

    if request.user != tender.customer and request.user.role != 'admin':
        return HttpResponseForbidden('Нет доступа.')

    if request.method == 'POST':
        tender.status = 'published'
        tender.notifications_sent = False
        tender.save()
        messages.success(request, 'Тендер опубликован.')
        return redirect('tender_detail', tender_id=tender.id)

    return render(request, 'publish_tender.html', {'tender': tender})


@login_required
def create_application(request, tender_id):
    close_expired_tenders()

    if request.user.role not in ['supplier', 'admin']:
        messages.error(request, 'У вас нет доступа к участию в тендерах.')
        return redirect('home')

    tender = get_object_or_404(Tender, id=tender_id)

    if tender.status != 'published':
        messages.error(request, 'Подавать заявку можно только на опубликованный тендер.')
        return redirect('tender_detail', tender_id=tender.id)

    if tender.deadline <= timezone.now():
        messages.error(request, 'Срок подачи заявок уже истёк.')
        return redirect('tender_detail', tender_id=tender.id)

    existing_application = Application.objects.filter(
        tender=tender,
        supplier=request.user
    ).first()

    if existing_application:
        messages.error(request, 'Вы уже подали заявку на этот тендер.')
        return redirect('tender_detail', tender_id=tender.id)

    if request.method == 'POST':
        price = request.POST.get('price')
        comment = request.POST.get('comment')

        if not price:
            messages.error(request, 'Введите цену.')
            return render(request, 'create_application.html', {'tender': tender})

        Application.objects.create(
            tender=tender,
            supplier=request.user,
            price=price,
            comment=comment
        )

        messages.success(request, 'Заявка отправлена.')
        return redirect('tender_detail', tender_id=tender.id)

    return render(request, 'create_application.html', {'tender': tender})


@login_required
def edit_application(request, application_id):
    application = get_object_or_404(Application, id=application_id)

    if request.user != application.supplier and request.user.role != 'admin':
        return HttpResponseForbidden('Нет доступа.')

    if application.tender.deadline <= timezone.now():
        messages.error(request, 'После дедлайна заявку изменять нельзя.')
        return redirect('tender_detail', tender_id=application.tender.id)

    if application.status == 'withdrawn':
        messages.error(request, 'Отозванную заявку изменять нельзя.')
        return redirect('tender_detail', tender_id=application.tender.id)

    if request.method == 'POST':
        application.price = request.POST.get('price')
        application.comment = request.POST.get('comment')
        application.save()

        messages.success(request, 'Заявка обновлена.')
        return redirect('tender_detail', tender_id=application.tender.id)

    return render(request, 'edit_application.html', {'application': application})


@login_required
def withdraw_application(request, application_id):
    application = get_object_or_404(Application, id=application_id)

    if request.user != application.supplier and request.user.role != 'admin':
        return HttpResponseForbidden('Нет доступа.')

    if application.tender.deadline <= timezone.now():
        messages.error(request, 'После дедлайна заявку отзывать нельзя.')
        return redirect('tender_detail', tender_id=application.tender.id)

    if request.method == 'POST':
        application.status = 'withdrawn'
        application.save()
        messages.success(request, 'Заявка отозвана.')
        return redirect('tender_detail', tender_id=application.tender.id)

    return render(request, 'withdraw_application.html', {'application': application})


@login_required
def choose_winner(request, tender_id):
    close_expired_tenders()
    tender = get_object_or_404(Tender, id=tender_id)

    if request.user != tender.customer and request.user.role != 'admin':
        return HttpResponseForbidden('Нет доступа.')

    if tender.status != 'closed':
        messages.error(request, 'Победителя можно выбрать только после закрытия тендера.')
        return redirect('tender_detail', tender_id=tender.id)

    if request.method == 'POST':
        application_id = request.POST.get('application_id')
        application = get_object_or_404(Application, id=application_id, tender=tender)

        tender.winner = application.supplier
        tender.save()

        tender.applications.exclude(id=application.id).update(status='lost')
        application.status = 'winner'
        application.save()

        messages.success(request, 'Победитель выбран.')
        return redirect('tender_detail', tender_id=tender.id)

    return render(request, 'choose_winner.html', {'tender': tender})


@login_required
def application_documents(request, application_id):
    application = get_object_or_404(Application, id=application_id)

    if request.user.role == 'supplier' and application.supplier != request.user:
        return HttpResponseForbidden('Нет доступа.')

    if request.user.role == 'customer' and application.tender.customer != request.user:
        return HttpResponseForbidden('Нет доступа.')

    if request.user.role not in ['supplier', 'customer', 'admin']:
        return HttpResponseForbidden('Нет доступа.')

    return render(request, 'application_documents.html', {
        'application': application,
        'documents': application.documents.all().order_by('-uploaded_at'),
    })


@login_required
def upload_document(request, application_id):
    application = get_object_or_404(Application, id=application_id)

    if request.user.role not in ['supplier', 'admin']:
        return HttpResponseForbidden('Нет доступа.')

    if request.user.role == 'supplier' and application.supplier != request.user:
        return HttpResponseForbidden('Нет доступа.')

    if application.tender.deadline <= timezone.now():
        messages.error(request, 'После дедлайна загружать документы нельзя.')
        return redirect('application_documents', application_id=application.id)

    if application.status == 'withdrawn':
        messages.error(request, 'Нельзя загружать документы в отозванную заявку.')
        return redirect('application_documents', application_id=application.id)

    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        description = request.POST.get('description')

        if not uploaded_file:
            messages.error(request, 'Выберите файл.')
            return render(request, 'upload_document.html', {'application': application})

        Document.objects.create(
            application=application,
            file=uploaded_file,
            description=description
        )

        messages.success(request, 'Документ загружен.')
        return redirect('application_documents', application_id=application.id)

    return render(request, 'upload_document.html', {'application': application})


@login_required
def delete_document(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    application = document.application

    if request.user.role not in ['supplier', 'admin']:
        return HttpResponseForbidden('Нет доступа.')

    if request.user.role == 'supplier' and application.supplier != request.user:
        return HttpResponseForbidden('Нет доступа.')

    if application.tender.deadline <= timezone.now():
        messages.error(request, 'После дедлайна удалять документы нельзя.')
        return redirect('application_documents', application_id=application.id)

    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Документ удалён.')
        return redirect('application_documents', application_id=application.id)

    return render(request, 'delete_document.html', {'document': document})


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        register_form = RegisterForm(request.POST)

        if register_form.is_valid():
            user = register_form.save()

            verification = VerificationRequest.objects.filter(user=user).last()

            if verification:
                send_mail(
                    subject='Новая заявка на верификацию',
                    message=f"""
Пользователь {user.username} отправил заявку на верификацию.

Тип доступа: {verification.request_type}
Организация: {verification.organization_name}
Email пользователя: {user.email}
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=False,
                )

            return redirect('verification_success')

    else:
        register_form = RegisterForm()

    return render(request, 'register.html', {'register_form': register_form})
