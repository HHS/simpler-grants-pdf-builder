from nofos.forms import create_object_model_form

from .models import CompareDocument

create_compare_form_class = create_object_model_form(CompareDocument)

CompareTitleForm = create_compare_form_class(["title"])
CompareGroupForm = create_compare_form_class(["group"])
