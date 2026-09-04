from django import forms

from .models import Document


class DocumentForm(forms.ModelForm):

    class Meta:
        model = Document

        fields = [
            "subject",
            "title",
            "file",
        ]

        widgets = {
            "subject": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Django Basics"
                }
            ),

            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control"
                }
            ),
        }

    def __init__(
        self,
        *args,
        user=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields["subject"].queryset = (
                self.fields["subject"]
                .queryset
                .filter(user=user)
            )