from django import forms


class QAForm(forms.Form):
    question = forms.CharField(
        label="Ask a question",
        max_length=1000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": (
                    "Ask something about this study material..."
                ),
            }
        ),
    )