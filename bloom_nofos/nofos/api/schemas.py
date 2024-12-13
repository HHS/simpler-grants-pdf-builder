from ninja import Schema
from typing import List, Optional


class SubsectionSchema(Schema):
    name: str
    html_id: str
    order: int
    tag: str
    body: str
    callout_box: bool = False
    html_class: str = ""


class SectionSchema(Schema):
    name: str
    html_id: str
    order: int
    has_section_page: bool
    subsections: List[SubsectionSchema]


class NofoSchema(Schema):
    title: str
    filename: str
    short_name: str
    number: str
    opdiv: str
    agency: str
    tagline: str
    application_deadline: str
    subagency: str = ""
    sections: List[SectionSchema]
    # Required fields with defaults
    theme: str = "portrait-hrsa-blue"
    cover: str = "nofo--cover-page--medium"
    icon_style: str = "nofo--icons--border"
    status: str = "draft"
    # Optional fields
    subagency2: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""
    cover_image: str = ""
    cover_image_alt_text: str = ""
    inline_css: str = ""


class ErrorSchema(Schema):
    message: str
    details: Optional[dict] = None


class SuccessSchema(Schema):
    message: str
