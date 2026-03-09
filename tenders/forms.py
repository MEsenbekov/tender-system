from django import forms
from django.contrib.auth import get_user_model
from .models import VerificationRequest

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput)

    request_type = forms.ChoiceField(
        label='Какой доступ вам нужен',
        choices=VerificationRequest.REQUEST_TYPE_CHOICES
    )
    organization_name = forms.CharField(label='Название организации')
    organization_type = forms.CharField(label='Тип организации', required=False)
    activity_description = forms.CharField(
        label='Описание деятельности',
        widget=forms.Textarea(attrs={'rows': 4})
    )
    address = forms.CharField(label='Адрес', required=False)
    phone = forms.CharField(label='Телефон')
    website = forms.URLField(label='Сайт', required=False)
    contact_person = forms.CharField(label='Контактное лицо')
    comment = forms.CharField(
        label='Комментарий',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3})
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('password2'):
            raise forms.ValidationError('Пароли не совпадают')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'user'

        if commit:
            user.save()

            VerificationRequest.objects.create(
                user=user,
                request_type=self.cleaned_data['request_type'],
                organization_name=self.cleaned_data['organization_name'],
                organization_type=self.cleaned_data['organization_type'],
                activity_description=self.cleaned_data['activity_description'],
                address=self.cleaned_data['address'],
                phone=self.cleaned_data['phone'],
                website=self.cleaned_data['website'],
                contact_person=self.cleaned_data['contact_person'],
                comment=self.cleaned_data['comment'],
                status='pending',
            )

        return user