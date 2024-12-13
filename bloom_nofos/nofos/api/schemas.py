from ninja import ModelSchema, Schema
from typing import List, Optional
from nofos.models import Nofo, Section, Subsection


class SubsectionSchema(ModelSchema):
    class Config:
        model = Subsection
        model_fields = [
            "name",
            "html_id",
            "order",
            "tag",
            "body",
            "callout_box",
            "html_class",
        ]
        model_fields_optional = ["html_class"]  # Fields that should have defaults


class SectionSchema(ModelSchema):
    subsections: List[SubsectionSchema]

    class Config:
        model = Section
        model_fields = ["name", "html_id", "order", "has_section_page"]


class NofoSchema(ModelSchema):
    sections: List[SectionSchema]

    class Config:
        model = Nofo
        model_fields = [
            "title",
            "filename",
            "short_name",
            "number",
            "opdiv",
            "agency",
            "tagline",
            "application_deadline",
            "subagency",
            "subagency2",
            "author",
            "subject",
            "keywords",
            "theme",
            "cover",
            "icon_style",
            "status",
            "cover_image",
            "cover_image_alt_text",
            "inline_css",
        ]
        model_fields_optional = [
            "subagency",
            "subagency2",
            "author",
            "subject",
            "keywords",
            "cover_image",
            "cover_image_alt_text",
            "inline_css",
        ]


class ErrorSchema(Schema):
    message: str
    details: Optional[dict] = None


class SuccessSchema(Schema):
    message: str
