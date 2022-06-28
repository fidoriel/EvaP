import random

from django.conf import settings
from django.utils.translation import get_language
from evap.evaluation.forms import NotebookForm


def slogan(request):
    if get_language() == "de":
        return {"slogan": random.choice(settings.SLOGANS_DE)}  # nosec
    return {"slogan": random.choice(settings.SLOGANS_EN)}  # nosec


def debug(request):
    return {"debug": settings.DEBUG}


def notebook_content(request):
    c={}
    if request.user.is_authenticated:
        c["notebook_form"] = NotebookForm(instance=request.user)
    return c
