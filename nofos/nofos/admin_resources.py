from import_export import resources
from .models import Nofo, Section, Subsection


class NofoResource(resources.ModelResource):
    class Meta:
        model = Nofo


class SectionResource(resources.ModelResource):
    class Meta:
        model = Section
        use_bulk = True
        batch_size = 1000


class SubsectionResource(resources.ModelResource):
    class Meta:
        model = Subsection
        use_bulk = True
        batch_size = 1000
