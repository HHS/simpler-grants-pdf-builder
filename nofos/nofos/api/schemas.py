from typing import List, Optional

from ninja import ModelSchema, Schema

from nofos.models import Nofo, Section, Subsection


class SubsectionSchema(ModelSchema):
    class Meta:
        model = Subsection
        fields = [
            "name",
            "html_id",
            "order",
            "tag",
            "body",
            "callout_box",
            "html_class",
        ]
        fields_optional = ["html_class"]  # Fields that should have defaults


class SectionBaseSchema(ModelSchema):
    class Meta:
        model = Section
        fields = ["name", "html_id", "order", "has_section_page", "html_class"]
        fields_optional = ["html_class"]


class SectionSchema(SectionBaseSchema):
    subsections: Optional[List[SubsectionSchema]]


class NofoBaseSchema(ModelSchema):
    class Meta:
        model = Nofo
        fields = [
            "id",
            "title",
            "filename",
            "short_name",
            "number",
            "opdiv",
            "agency",
            "tagline",
            "application_deadline",
            "theme",
            "cover",
            "icon_style",
            "status",
        ]
        fields_optional = [
            "subagency",
            "subagency2",
            "author",
            "subject",
            "keywords",
            "cover_image",
            "cover_image_alt_text",
            "inline_css",
            "before_you_begin",
        ]


class NofoSchema(NofoBaseSchema):
    sections: List[SectionSchema]


class ErrorSchema(Schema):
    message: str
    details: Optional[dict] = None


class SuccessSchema(Schema):
    nofo: NofoSchema
