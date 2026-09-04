from django import forms

from .models import Note


class NoteForm(forms.ModelForm):

    class Meta:
        model = Note
        fields = ["subject", "title", "content"]

        widgets = {
            "subject": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Python Functions"
                }
            ),

            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 12,
                    "placeholder": "Write your study notes here..."
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is not None:
            self.fields["subject"].queryset = (
                self.fields["subject"]
                .queryset
                .filter(user=user)
            )