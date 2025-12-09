import json

from composer.conditional.conditional_questions import CONDITIONAL_QUESTIONS
from composer.models import (
    ContentGuide,
    ContentGuideInstance,
    ContentGuideSection,
    ContentGuideSubsection,
)
from composer.views import WriterInstanceConditionalQuestionView
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

User = get_user_model()


class BaseWriterViewTests(TestCase):
    """
    Base test case for Writer views.

    - Creates shared bloom/acf/hrsa users once for all subclasses.
    - Provides small helpers for common objects.
    """

    @classmethod
    def setUpTestData(cls):
        cls.password = "testpass123"

        cls.bloom_user = User.objects.create_user(
            email="bloom@example.com",
            password=cls.password,
            group="bloom",
            force_password_reset=False,
        )
        cls.acf_user = User.objects.create_user(
            email="acf@example.com",
            password=cls.password,
            group="acf",
            force_password_reset=False,
        )
        cls.hrsa_user = User.objects.create_user(
            email="hrsa@example.com",
            password=cls.password,
            group="hrsa",
            force_password_reset=False,
        )

    # Optional convenience helpers; use them where you like
    def login_as(self, user):
        self.client.login(email=user.email, password=self.password)

    def create_acf_parent_guide(self, **overrides):
        data = {
            "title": "ACF Core Content Guide",
            "opdiv": "acf",
            "group": "acf",
            "status": "published",
        }
        data.update(overrides)
        return ContentGuide.objects.create(**data)


class WriterDashboardViewTests(BaseWriterViewTests):
    def setUp(self):
        super().setUp()
        self.url = reverse("composer:writer_index")

    def test_anonymous_user_is_redirected_to_login(self):
        """Anonymous users should be redirected to the login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)

    def test_logged_in_user_sees_dashboard_headings(self):
        """
        Logged-in users should see the Writer dashboard.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Welcome to Composer")

    def test_non_bloom_user_sees_only_their_group_instances_and_published_guides(self):
        """
        A non-bloom user only sees ContentGuideInstances and published ContentGuides
        whose group matches their own.
        """
        # Instances
        acf_instance = ContentGuideInstance.objects.create(
            title="ACF Draft NOFO",
            opdiv="acf",
            group="acf",
        )
        hrsa_instance = ContentGuideInstance.objects.create(
            title="HRSA Draft NOFO",
            opdiv="hrsa",
            group="hrsa",
        )

        # Guides
        acf_guide = ContentGuide.objects.create(
            title="ACF Content Guide",
            opdiv="acf",
            group="acf",
            status="published",
        )
        hrsa_guide = ContentGuide.objects.create(
            title="HRSA Content Guide",
            opdiv="hrsa",
            group="hrsa",
            status="published",
        )
        _draft_guide = ContentGuide.objects.create(
            title="Draft Content Guide",
            opdiv="acf",
            group="acf",
            status="draft",
        )

        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        draft_nofos = list(response.context["draft_nofos"])
        content_guides = list(response.context["content_guides"])

        # Only the ACF objects should be visible
        self.assertIn(acf_instance, draft_nofos)
        self.assertNotIn(hrsa_instance, draft_nofos)

        self.assertIn(acf_guide, content_guides)
        self.assertNotIn(hrsa_guide, content_guides)

    def test_bloom_user_sees_all_groups_instances_and_published_guides(self):
        """
        A bloom user can see ALL groups' ContentGuideInstances and published ContentGuides.
        """
        acf_instance = ContentGuideInstance.objects.create(
            title="ACF Draft NOFO",
            opdiv="acf",
            group="acf",
        )
        hrsa_instance = ContentGuideInstance.objects.create(
            title="HRSA Draft NOFO",
            opdiv="hrsa",
            group="hrsa",
        )

        acf_guide = ContentGuide.objects.create(
            title="ACF Content Guide",
            opdiv="acf",
            group="acf",
            status="published",
        )
        hrsa_guide = ContentGuide.objects.create(
            title="HRSA Content Guide",
            opdiv="hrsa",
            group="hrsa",
            status="published",
        )
        _draft_guide = ContentGuide.objects.create(
            title="Draft Content Guide",
            opdiv="bloom",
            group="bloom",
            status="draft",
        )

        self.client.login(email="bloom@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        draft_nofos = set(response.context["draft_nofos"])
        content_guides = set(response.context["content_guides"])

        self.assertEqual(draft_nofos, {acf_instance, hrsa_instance})
        self.assertEqual(content_guides, {acf_guide, hrsa_guide})


class WriterInstanceBeforeStartViewTests(BaseWriterViewTests):
    def setUp(self):
        super().setUp()
        self.url = reverse("composer:writer_before_start")

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_page_renders_for_logged_in_user(self):
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Before you begin")


class WriterInstanceStartViewTests(BaseWriterViewTests):
    def setUp(self):
        super().setUp()
        self.url = reverse("composer:writer_start")

    def test_anonymous_user_is_redirected_to_login(self):
        """Anonymous users should be redirected to the login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)

    def test_get_renders_start_page_for_logged_in_user(self):
        """
        Logged-in users should see the start page with the expected heading
        and the form to choose a content guide.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Start drafting a new NOFO")

    def test_non_bloom_user_sees_only_their_group_content_guides(self):
        """
        Non-bloom users only see ContentGuides from their own group
        in the radio list.
        """
        acf_guide = ContentGuide.objects.create(
            title="ACF Guide",
            opdiv="acf",
            group="acf",
            status="published",
        )
        hrsa_guide = ContentGuide.objects.create(
            title="HRSA Guide",
            opdiv="hrsa",
            group="hrsa",
            status="published",
        )

        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Should show ACF guide but not HRSA guide
        self.assertContains(response, acf_guide.title)
        self.assertNotContains(response, hrsa_guide.title)

    def test_bloom_user_sees_all_content_guides(self):
        """
        Bloom users can see ContentGuides from all groups in the radio list.
        """
        acf_guide = ContentGuide.objects.create(
            title="ACF Guide",
            opdiv="acf",
            group="acf",
            status="published",
        )
        hrsa_guide = ContentGuide.objects.create(
            title="HRSA Guide",
            opdiv="hrsa",
            group="hrsa",
            status="published",
        )

        self.client.login(email="bloom@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, acf_guide.title)
        self.assertContains(response, hrsa_guide.title)

    def test_valid_post_redirects_to_details_step(self):
        """
        When a valid parent is chosen, redirect to the writer_details step
        with parent_pk in the URL.
        """
        guide = ContentGuide.objects.create(
            title="ACF Guide",
            opdiv="acf",
            group="acf",
            status="published",
        )
        self.client.login(email="acf@example.com", password="testpass123")

        response = self.client.post(self.url, data={"parent": str(guide.pk)})
        self.assertEqual(response.status_code, 302)

        expected_url = reverse(
            "composer:writer_details",
            kwargs={"parent_pk": str(guide.pk)},
        )
        self.assertEqual(response.url, expected_url)

    def test_invalid_post_shows_error_message(self):
        """
        If no parent is selected, the form should be redisplayed with a validation error.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.post(self.url, data={})  # no parent
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("parent", form.errors)
        self.assertEqual(form.errors["parent"], ["This field is required."])


class WriterInstanceDetailsViewTests(BaseWriterViewTests):
    def setUp(self):
        super().setUp()

        # Parent content guide (ACF)
        self.parent_guide = self.create_acf_parent_guide()

        self.url = reverse(
            "composer:writer_details",
            kwargs={"parent_pk": str(self.parent_guide.pk)},
        )

    def test_anonymous_user_gets_403_permissions_error(self):
        """Anonymous users should be redirected to the login page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_non_bloom_wrong_group_gets_404(self):
        """
        A non-bloom user cannot access a content guide that doesn't match their group.
        """
        self.client.login(email="hrsa@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_bloom_user_can_access_any_group_guide(self):
        """
        A bloom user can access the details page even if the guide group differs.
        """
        self.client.login(email="bloom@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "First, let’s set up the program details")
        self.assertContains(response, self.parent_guide.title)

    def test_get_populates_context_for_same_group_user(self):
        """
        GET: same-group user sees page, with parent_content_guide and agency_name in context.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Heading and parent title
        self.assertContains(response, "First, let’s set up the program details")
        self.assertContains(response, self.parent_guide.title)

        # Context variables
        self.assertEqual(response.context["parent_content_guide"], self.parent_guide)
        self.assertEqual(response.context["agency_name"], "acf")

    def test_valid_post_creates_instance_and_redirects(self):
        """
        POST with valid data should create a ContentGuideInstance linked to the parent
        and redirect back to the writer dashboard.
        """
        self.client.login(email="acf@example.com", password="testpass123")

        data = {
            "opdiv": "acf",
            "agency": "Some ACF Office",
            "title": "My First Draft NOFO",
            "short_name": "First Draft",
            "number": "ACF-123",
            # New metadata fields using the updated widgets
            "author": "Jane Doe",
            "subject": "Health equity program",
            "keywords": "health, equity, child welfare",
        }
        response = self.client.post(self.url, data=data)

        # Instance was created
        instance = ContentGuideInstance.objects.get(title="My First Draft NOFO")
        self.assertEqual(instance.parent, self.parent_guide)
        self.assertEqual(instance.group, "acf")
        self.assertEqual(instance.opdiv, "acf")
        self.assertEqual(instance.agency, "Some ACF Office")
        self.assertEqual(instance.short_name, "First Draft")
        self.assertEqual(instance.number, "ACF-123")

        # New field assertions
        self.assertEqual(instance.author, "Jane Doe")
        self.assertEqual(instance.subject, "Health equity program")
        self.assertEqual(instance.keywords, "health, equity, child welfare")

        # Should redirect to first page of yes/no questions
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                "composer:writer_conditional_questions",
                kwargs={"pk": str(instance.pk), "page": 1},
            ),
        )

    def test_invalid_post_shows_errors_and_does_not_create_instance(self):
        """
        Missing required fields (e.g., opdiv and title) should keep user on the page,
        show an error summary, and not create any instances.
        """
        self.client.login(email="acf@example.com", password="testpass123")

        # Post with no data at all
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 200)  # form re-rendered

        # No instances created
        self.assertEqual(ContentGuideInstance.objects.count(), 0)

        # Error summary included
        self.assertContains(response, "Error submitting form")
        self.assertContains(response, "usa-alert--error")

        # Field-level errors
        form = response.context["form"]
        self.assertIn("opdiv", form.errors)
        self.assertEqual(form.errors["opdiv"], ["This field is required."])

        self.assertIn("title", form.errors)
        self.assertEqual(form.errors["title"], ["This field is required."])


class GetWriterConditionalQuestionsPageTitleTests(SimpleTestCase):
    def setUp(self):
        # You don't need a full CBV setup; direct instantiation is fine
        self.view = WriterInstanceConditionalQuestionView()

    def test_page_title_for_known_pages(self):
        self.assertEqual(
            self.view.get_page_title(1),
            "Great! Let’s add a few details about your program",
        )
        self.assertEqual(
            self.view.get_page_title(2),
            "Tell us about the attachments you require from applicants",
        )

    def test_page_title_defaults_for_unknown_page(self):
        # page 3 isn't in the mapping, so we expect the default
        self.assertEqual(
            self.view.get_page_title(3),
            "Great! Let’s add a few details about your program",
        )


class WriterInstanceConditionalQuestionViewTests(BaseWriterViewTests):
    def setUp(self):
        super().setUp()

        # Parent content guide (ACF)
        self.parent_guide = self.create_acf_parent_guide()

        # Draft NOFO instance based on the guide
        self.instance = ContentGuideInstance.objects.create(
            title="My First Draft NOFO",
            short_name="First Draft",
            opdiv="acf",
            group="acf",
            parent=self.parent_guide,
            conditional_questions={},
        )

        self.url_page1 = reverse(
            "composer:writer_conditional_questions",
            kwargs={"pk": str(self.instance.pk), "page": 1},
        )
        self.url_page2 = reverse(
            "composer:writer_conditional_questions",
            kwargs={"pk": str(self.instance.pk), "page": 2},
        )

    def test_anonymous_user_gets_403_permissions_error(self):
        """Anonymous users should get a 403 (per project LoginRequired behavior)."""
        response = self.client.get(self.url_page1)
        self.assertEqual(response.status_code, 403)

    def test_non_bloom_wrong_group_gets_403(self):
        """
        A non-bloom user cannot access a ContentGuideInstance that doesn't match their group.
        """
        self.client.login(email="hrsa@example.com", password="testpass123")
        response = self.client.get(self.url_page1)
        self.assertEqual(response.status_code, 403)

    def test_bloom_user_can_access_any_group_instance(self):
        """
        A bloom user can access the conditional questions page even if groups differ.
        """
        self.client.login(email="bloom@example.com", password="testpass123")
        response = self.client.get(self.url_page1)
        self.assertEqual(response.status_code, 200)
        # Page 1 title
        self.assertContains(
            response, "Great! Let’s add a few details about your program"
        )

    def test_same_group_user_can_access_instance(self):
        """
        Same-group user (acf) can access the conditional questions page.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url_page1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["page_title"],
            "Great! Let’s add a few details about your program",
        )

    def test_page_with_no_questions_returns_404(self):
        """
        Requesting a page number with no questions should return 404.
        """
        self.client.login(email="acf@example.com", password="testpass123")

        # Assuming our JSON only has pages 1 and 2,
        # a higher page like 3 should not have any questions.
        url_page3 = reverse(
            "composer:writer_conditional_questions",
            kwargs={"pk": str(self.instance.pk), "page": 3},
        )
        response = self.client.get(url_page3)
        self.assertEqual(response.status_code, 404)

    def test_valid_post_on_page1_saves_answers_and_redirects_to_next_page(self):
        """
        POST on page 1 should save boolean answers for page 1 questions,
        preserve other keys in conditional_questions, and redirect to the next page.
        """
        self.client.login(email="acf@example.com", password="testpass123")

        # Build POST data based on page 1 keys in the JSON
        post_data = {
            "cost_sharing": "true",
            "maintenance_of_effort": "false",
            "data_management_plans": "true",
            "training_awards": "false",
            "foreign_awards": "true",
            "intergovernmental_review": "false",
            "cooperative_agreement": "true",
        }

        response = self.client.post(self.url_page1, data=post_data)
        # Should redirect to page 2 (next page)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url_page2)

        # Reload instance from DB
        self.instance.refresh_from_db()
        cq = self.instance.conditional_questions

        # Page 1 answers saved as booleans
        self.assertEqual(cq["cost_sharing"], True)
        self.assertEqual(cq["maintenance_of_effort"], False)
        self.assertEqual(cq["data_management_plans"], True)
        self.assertEqual(cq["training_awards"], False)
        self.assertEqual(cq["foreign_awards"], True)
        self.assertEqual(cq["intergovernmental_review"], False)
        self.assertEqual(cq["cooperative_agreement"], True)

    def test_subset_of_answers_on_page1_causes_error(self):
        """
        POST with not all keys expected should raise an error summary with each field required.
        """
        self.client.login(email="acf@example.com", password="testpass123")

        # Only 1 key, missing 6 others
        post_data = {"cost_sharing": "true"}

        response = self.client.post(self.url_page1, data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.path, self.url_page1)

        page_2_questions = [
            q.label
            for q in CONDITIONAL_QUESTIONS.for_page(1)
            if q.key != "cost_sharing"
        ]
        for question in page_2_questions:
            self.assertContains(
                response, "{}: This field is required.".format(question)
            )

        # Reload instance from DB
        self.instance.refresh_from_db()
        cq = self.instance.conditional_questions
        # "cost_sharing" key did not get saved
        self.assertNotIn("cost_sharing", cq)

    def test_valid_post_on_last_page_redirects_to_writer_confirmation_and_sets_message(
        self,
    ):
        """
        POST on the last page should save answers and redirect to the writer index with
        a success message that uses the instance's name.
        """
        self.client.login(email="acf@example.com", password="testpass123")

        post_data = {
            "table_of_contents": "true",
            "indirect_cost_agreement": "true",
            "resumes_and_job_descriptions": "true",
            "organizational_chart": "true",
            "letters_of_support": "true",
            "report_on_overlap": "true",
        }

        response = self.client.post(self.url_page2, data=post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse(
                "composer:writer_confirmation", kwargs={"pk": str(self.instance.pk)}
            ),
        )

        # Instance updated
        self.instance.refresh_from_db()
        cq = self.instance.conditional_questions

        self.assertEqual(cq["table_of_contents"], True)
        self.assertEqual(cq["indirect_cost_agreement"], True)
        self.assertEqual(cq["resumes_and_job_descriptions"], True)
        self.assertEqual(cq["organizational_chart"], True)
        self.assertEqual(cq["letters_of_support"], True)
        self.assertEqual(cq["report_on_overlap"], True)

        # Success message present
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("Draft NOFO “First Draft” created successfully." in m for m in messages)
        )


class WriterInstanceConfirmationViewTests(BaseWriterViewTests):
    def setUp(self):
        super().setUp()

        # Parent content guide (ACF)
        self.parent_guide = self.create_acf_parent_guide()

        # Draft NOFO instance with some details + conditional answers
        self.instance = ContentGuideInstance.objects.create(
            opdiv="acf",
            agency="Some ACF Office",
            title="My Draft NOFO",
            short_name="Draft 1",
            number="ACF-123",
            group="acf",
            parent=self.parent_guide,
            conditional_questions={
                # page 1
                "cost_sharing": True,
                "maintenance_of_effort": False,
                # page 2
                "letters_of_support": True,
                "table_of_contents": False,
            },
        )

        self.confirmation_url = reverse(
            "composer:writer_confirmation", kwargs={"pk": str(self.instance.pk)}
        )

        # For later URL comparisons
        self.details_url = reverse(
            "composer:writer_details",
            kwargs={"parent_pk": str(self.parent_guide.pk)},
        )
        self.page1_url = reverse(
            "composer:writer_conditional_questions",
            kwargs={"pk": str(self.instance.pk), "page": 1},
        )
        self.page2_url = reverse(
            "composer:writer_conditional_questions",
            kwargs={"pk": str(self.instance.pk), "page": 2},
        )
        self.writer_index_url = reverse("composer:writer_index")

    def test_anonymous_user_gets_403_permissions_error(self):
        """
        Anonymous users should get a 403 (per LoginRequiredMixin behavior in this project).
        """
        response = self.client.get(self.confirmation_url)
        self.assertEqual(response.status_code, 403)

    def test_non_bloom_wrong_group_gets_403(self):
        """
        A non-bloom user whose group doesn't match the instance's group gets 403.
        """
        self.client.login(email="hrsa@example.com", password="testpass123")
        response = self.client.get(self.confirmation_url)
        self.assertEqual(response.status_code, 403)

    def test_bloom_user_can_access_any_group_instance(self):
        """
        Bloom users can access the confirmation page for any group.
        """
        self.client.login(email="bloom@example.com", password="testpass123")
        response = self.client.get(self.confirmation_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "This information is ready to be added to your draft NOFO",
        )

    def test_same_group_user_sees_details_and_questions(self):
        """
        Same-group user sees the confirmation page with details and conditional questions rendered.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.confirmation_url)
        self.assertEqual(response.status_code, 200)

        # Heading
        self.assertContains(
            response,
            "This information is ready to be added to your draft NOFO",
        )

        # Page 1 conditional questions: should show label + mapped Yes/No
        page1_questions = CONDITIONAL_QUESTIONS.for_page(1)
        # cost_sharing is True -> "Yes"
        cost_sharing = next(q for q in page1_questions if q.key == "cost_sharing")
        self.assertContains(response, cost_sharing.label)
        self.assertContains(response, "Yes")

        # maintenance_of_effort is False -> "No"
        moe = next(q for q in page1_questions if q.key == "maintenance_of_effort")
        self.assertContains(response, moe.label)
        self.assertContains(response, "No")

        # Page 2 conditional questions: letters_of_support True, table_of_contents False
        page2_questions = CONDITIONAL_QUESTIONS.for_page(2)
        los = next(q for q in page2_questions if q.key == "letters_of_support")
        toc = next(q for q in page2_questions if q.key == "table_of_contents")

        self.assertContains(response, los.label)
        self.assertContains(response, "Yes")  # letters_of_support=True
        self.assertContains(response, toc.label)
        self.assertContains(response, "No")  # table_of_contents=False

    def test_post_creates_sections_and_subsections_from_parent_guide(self):
        """
        POST to confirmation page creates ContentGuideInstanceSection and
        ContentGuideInstanceSubsection objects based on the parent ContentGuide.
        """
        # Create sections and subsections in the parent guide
        section1 = ContentGuideSection.objects.create(
            content_guide=self.parent_guide,
            order=1,
            name="Basic Information",
            html_id="sec-basic",
        )
        subsection1a = ContentGuideSubsection.objects.create(
            section=section1,
            order=1,
            name="Program Overview",
            tag="h3",
            body="This is the program overview.",
            edit_mode="full",
        )
        subsection1b = ContentGuideSubsection.objects.create(
            section=section1,
            order=2,
            name="Agency Details",
            tag="h3",
            body="This is agency details, with { variable }.",
            edit_mode="variables",
        )

        section2 = ContentGuideSection.objects.create(
            content_guide=self.parent_guide,
            order=2,
            name="Funding Details",
            html_id="sec-funding",
        )
        subsection2a = ContentGuideSubsection.objects.create(
            section=section2,
            order=1,
            name="Award Information",
            tag="h3",
            body="Award information goes here.",
            edit_mode="locked",
        )

        # Before POST, instance should have no sections/subsections
        self.assertEqual(self.instance.sections.count(), 0)

        # Login and POST
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.post(self.confirmation_url)

        # Should redirect to the writer section view for the first section
        first_instance_section = self.instance.sections.order_by("order", "pk").first()
        self.assertIsNotNone(first_instance_section)
        expected_redirect = reverse(
            "composer:writer_section_view",
            kwargs={
                "pk": str(self.instance.pk),
                "section_pk": str(first_instance_section.pk),
            },
        )
        self.assertRedirects(response, "{}?new_instance=1".format(expected_redirect))

        # Check that sections were created
        instance_sections = list(self.instance.sections.order_by("order", "pk"))
        self.assertEqual(len(instance_sections), 2)

        # Verify section 1
        inst_sec1 = instance_sections[0]
        self.assertEqual(inst_sec1.name, "Basic Information")
        self.assertEqual(inst_sec1.html_id, "sec-basic")
        self.assertEqual(inst_sec1.order, 1)

        # Verify section 2
        inst_sec2 = instance_sections[1]
        self.assertEqual(inst_sec2.name, "Funding Details")
        self.assertEqual(inst_sec2.html_id, "sec-funding")
        self.assertEqual(inst_sec2.order, 2)

        # Check that subsections were created for section 1
        inst_subsections1 = list(inst_sec1.subsections.order_by("order", "pk"))
        self.assertEqual(len(inst_subsections1), 2)
        self.assertEqual(inst_subsections1[0].name, "Program Overview")
        self.assertEqual(inst_subsections1[0].body, "This is the program overview.")
        self.assertEqual(inst_subsections1[0].edit_mode, "full")
        self.assertEqual(inst_subsections1[1].name, "Agency Details")
        self.assertEqual(
            inst_subsections1[1].body, "This is agency details, with { variable }."
        )
        self.assertEqual(inst_subsections1[1].edit_mode, "variables")

        # Check that subsections were created for section 2
        inst_subsections2 = list(inst_sec2.subsections.order_by("order", "pk"))
        self.assertEqual(len(inst_subsections2), 1)
        self.assertEqual(inst_subsections2[0].name, "Award Information")
        self.assertEqual(inst_subsections2[0].body, "Award information goes here.")
        self.assertEqual(inst_subsections2[0].edit_mode, "locked")

    def test_post_includes_only_conditional_subsections_matching_answers(self):
        """
        POST to confirmation page should include/exclude conditional subsections
        based on the instance's conditional question answers.
        """
        # Create a section with conditional subsections
        section = ContentGuideSection.objects.create(
            content_guide=self.parent_guide,
            order=1,
            name="Funding Policies",
            html_id="sec-policies",
        )

        # Non-conditional subsection (always included) -- no instructions, so not conditional
        ContentGuideSubsection.objects.create(
            section=section,
            order=1,
            name="General Policies",
            tag="h3",
            body="General policies body.",
            edit_mode="full",
        )

        # Conditional subsection for cost_sharing=True
        ContentGuideSubsection.objects.create(
            section=section,
            order=2,
            name="Cost Sharing",
            tag="h3",
            body="Cost sharing body.",
            edit_mode="full",
            instructions="Instructions indicating this is conditional: (YES)",
        )

        # Conditional subsection for maintenance_of_effort=False
        ContentGuideSubsection.objects.create(
            section=section,
            order=4,
            name="Maintenance of effort",
            tag="h3",
            body="No MOE body.",
            edit_mode="full",
            instructions="Instructions indicating this is conditional: (NO)",
        )

        # Conditional subsection for maintenance_of_effort=True (should NOT be included)
        ContentGuideSubsection.objects.create(
            section=section,
            order=5,
            name="Maintenance of effort",
            tag="h3",
            body="MOE required body.",
            edit_mode="full",
            instructions="Instructions indicating this is conditional: (YES)",
        )

        # Recall: self.instance has cost_sharing=True, maintenance_of_effort=False
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.post(self.confirmation_url)

        # Should redirect successfully
        self.assertEqual(response.status_code, 302)

        # Check created subsections
        instance_section = self.instance.sections.first()
        self.assertIsNotNone(instance_section)

        subsections = list(instance_section.subsections.order_by("order", "pk"))
        self.assertEqual(len(subsections), 3)

        subsection_names = [sub.name for sub in subsections]
        self.assertIn("General Policies", subsection_names)
        self.assertIn("Cost Sharing", subsection_names)

        self.assertIn("Maintenance of effort", subsection_names)
        # Confirm Maintenance of effort is the "No" option
        moe_sub = next(
            sub for sub in subsections if sub.name == "Maintenance of effort"
        )
        self.assertEqual(moe_sub.body, "No MOE body.")

    def test_post_handles_conditional_subsection_without_matching_question(self):
        """
        If a conditional subsection doesn't have a matching question in the registry,
        it should be skipped (not create an error).
        """
        section = ContentGuideSection.objects.create(
            content_guide=self.parent_guide,
            order=1,
            name="Test Section",
            html_id="sec-test",
        )

        # Conditional subsection with a name that doesn't match any question
        ContentGuideSubsection.objects.create(
            section=section,
            order=1,
            name="Nonexistent Conditional Question",
            tag="h3",
            body="This should be skipped.",
            edit_mode="full",
            instructions="Instructions indicating this is conditional: (YES)",
        )

        # Non-conditional subsection -- no instructions, so not conditional
        ContentGuideSubsection.objects.create(
            section=section,
            order=2,
            name="Regular Subsection",
            tag="h3",
            body="This should be included.",
            edit_mode="full",
        )

        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.post(self.confirmation_url)

        # Should not error
        self.assertEqual(response.status_code, 302)

        # Only the non-conditional subsection should be created
        instance_section = self.instance.sections.first()
        self.assertIsNotNone(instance_section)

        subsections = list(instance_section.subsections.all())
        self.assertEqual(len(subsections), 1)
        self.assertEqual(subsections[0].name, "Regular Subsection")

    def test_post_preserves_subsection_attributes(self):
        """
        Verify that subsection attributes (instructions, optional, etc.) are
        correctly copied from parent guide to instance.
        """
        from composer.models import ContentGuideSection, ContentGuideSubsection

        section = ContentGuideSection.objects.create(
            content_guide=self.parent_guide,
            order=1,
            name="Test Section",
            html_id="sec-test",
        )

        ContentGuideSubsection.objects.create(
            section=section,
            order=1,
            name="Test Subsection",
            tag="h4",
            body="Test body with {variable}.",
            edit_mode="variables",
            optional=True,
            instructions="These are instructions for the writer.",
        )

        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.post(self.confirmation_url)

        self.assertEqual(response.status_code, 302)

        instance_section = self.instance.sections.first()
        subsection = instance_section.subsections.first()

        # Verify all attributes were copied
        self.assertEqual(subsection.name, "Test Subsection")
        self.assertEqual(subsection.tag, "h4")
        self.assertEqual(subsection.body, "Test body with {variable}.")
        self.assertEqual(subsection.edit_mode, "variables")
        self.assertEqual(subsection.optional, True)
        self.assertEqual(
            subsection.instructions, "These are instructions for the writer."
        )


class WriterSectionViewAlertsTests(TestCase):
    def setUp(self):
        # Auth user in bloom group
        self.user = User.objects.create_user(
            email="writer@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
            force_password_reset=False,
        )
        self.client.login(email="writer@example.com", password="testpass123")

        # Base ContentGuide used as parent
        self.guide = ContentGuide.objects.create(
            title="Guide",
            opdiv="CDC",
            group="bloom",
        )

    def _create_instance_with_two_sections_and_not_started_subsections(self):
        """
        Helper: create a ContentGuideInstance with two sections, each having at least
        one 'not started' subsection (edit_mode != 'locked' and status == 'default').
        """
        instance = ContentGuideInstance.objects.create(
            title="My Draft NOFO",
            opdiv="CDC",
            group="bloom",
            parent=self.guide,
        )

        sec1 = ContentGuideSection.objects.create(
            content_guide_instance=instance,
            order=1,
            name="Instance Section 1",
            html_id="is1",
        )
        sec2 = ContentGuideSection.objects.create(
            content_guide_instance=instance,
            order=2,
            name="Instance Section 2",
            html_id="is2",
        )

        # For both sections, create at least one eligible "not started" subsection
        ContentGuideSubsection.objects.create(
            section=sec1,
            order=1,
            name="Sec1 Sub 1",
            tag="h4",
            body="Body",
            edit_mode="full",
            status="default",
        )
        ContentGuideSubsection.objects.create(
            section=sec2,
            order=1,
            name="Sec2 Sub 1",
            tag="h4",
            body="Body",
            edit_mode="full",
            status="default",
        )

        return instance, sec1, sec2

    def test_new_instance_first_section_shows_created_alert_not_not_started(self):
        """
        ?new_instance=1 on the first section:
        - shows the 'created' alert
        - hides the 'not started' alert
        """
        instance, sec1, _ = (
            self._create_instance_with_two_sections_and_not_started_subsections()
        )

        url = reverse(
            "composer:writer_section_view",
            kwargs={"pk": instance.pk, "section_pk": sec1.pk},
        )
        resp = self.client.get(f"{url}?new_instance=1")
        self.assertEqual(resp.status_code, 200)

        # Should show the "created" alert
        self.assertContains(resp, "Your draft NOFO has been created!")
        # Should not show the "not started" alert
        self.assertNotContains(resp, "You have not started some sections")

    def test_new_instance_second_section_shows_no_created_and_no_not_started_alert(
        self,
    ):
        """
        ?new_instance=1 on the second section:
        - does NOT show the 'created' alert (first section only)
        - does NOT show the 'not started' alert (suppressed by new_instance)
        """
        instance, _, sec2 = (
            self._create_instance_with_two_sections_and_not_started_subsections()
        )

        url = reverse(
            "composer:writer_section_view",
            kwargs={"pk": instance.pk, "section_pk": sec2.pk},
        )
        resp = self.client.get(f"{url}?new_instance=1")
        self.assertEqual(resp.status_code, 200)

        # Should not show either alert
        self.assertNotContains(resp, "Your draft NOFO has been created!")
        self.assertNotContains(resp, "You have not started some sections")

    def test_first_section_without_new_instance_shows_not_started_alert_only(self):
        """
        No new_instance param on first section:
        - does NOT show the 'created' alert
        - DOES show the 'not started' alert
        """
        instance, sec1, _ = (
            self._create_instance_with_two_sections_and_not_started_subsections()
        )

        url = reverse(
            "composer:writer_section_view",
            kwargs={"pk": instance.pk, "section_pk": sec1.pk},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Should NOT show the "created" alert
        self.assertNotContains(resp, "Your draft NOFO has been created!")
        # Should show the "not started" alert
        self.assertContains(resp, "You have not started some sections")


class WriterInstanceSubsectionEditViewTests(BaseWriterViewTests):
    def setUp(self):
        super().setUp()

        # Parent content guide (ACF)
        self.parent_guide = self.create_acf_parent_guide()

        # Draft NOFO instance
        self.instance = ContentGuideInstance.objects.create(
            title="My Draft NOFO",
            short_name="Draft 1",
            opdiv="acf",
            group="acf",
            parent=self.parent_guide,
        )

        # Section and subsection
        self.section = ContentGuideSection.objects.create(
            content_guide_instance=self.instance,
            order=1,
            name="Section 1",
            html_id="sec-1",
        )
        self.subsection_edit_full = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Subsection 1",
            tag="h3",
            body="Initial body content.",
            edit_mode="full",
        )

        self.url_full = reverse(
            "composer:writer_subsection_edit",
            kwargs={
                "pk": str(self.instance.pk),
                "section_pk": str(self.section.pk),
                "subsection_pk": str(self.subsection_edit_full.pk),
            },
        )

        self.subsection_edit_variables = ContentGuideSubsection.objects.create(
            section=self.section,
            order=2,
            name="Subsection 2",
            tag="h3",
            body="Initial body with { variable }.",
            edit_mode="variables",
            variables=json.dumps(
                {"variable": {"key": "variable", "type": "string", "label": "variable"}}
            ),
        )

        self.url_variables = reverse(
            "composer:writer_subsection_edit",
            kwargs={
                "pk": str(self.instance.pk),
                "section_pk": str(self.section.pk),
                "subsection_pk": str(self.subsection_edit_variables.pk),
            },
        )

        self.subsection_optional = ContentGuideSubsection.objects.create(
            section=self.section,
            order=3,
            name="Subsection 3",
            tag="h3",
            body="Optional subsection body.",
            edit_mode="locked",
            optional=True,
        )

        self.url_optional = reverse(
            "composer:writer_subsection_edit",
            kwargs={
                "pk": str(self.instance.pk),
                "section_pk": str(self.section.pk),
                "subsection_pk": str(self.subsection_optional.pk),
            },
        )

    def test_anonymous_user_gets_403_permissions_error(self):
        """Anonymous users should get a 403 (per LoginRequiredMixin behavior)."""
        response = self.client.get(self.url_full)
        self.assertEqual(response.status_code, 403)

    def test_non_bloom_wrong_group_gets_403(self):
        """
        A non-bloom user whose group doesn't match the instance's group gets 403.
        """
        self.client.login(email="hrsa@example.com", password="testpass123")
        response = self.client.get(self.url_full)
        self.assertEqual(response.status_code, 403)

    def test_bloom_user_can_access_any_group_instance(self):
        """
        Bloom users can access the subsection edit page for any group.
        """
        self.client.login(email="bloom@example.com", password="testpass123")
        response = self.client.get(self.url_full)
        self.assertEqual(response.status_code, 200)

    def test_same_group_user_can_access_subsection_edit(self):
        """
        Same-group user can access the subsection edit page.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url_full)
        self.assertEqual(response.status_code, 200)

    def test_post_updates_edit_full_subsection_body_and_redirects(self):
        """
        POST with new body content should update the subsection and redirect
        back to the section view.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        new_body = "Updated body content."
        response = self.client.post(self.url_full, data={"body": new_body})
        self.assertEqual(response.status_code, 302)
        url = reverse(
            "composer:writer_section_view",
            kwargs={
                "pk": str(self.instance.pk),
                "section_pk": str(self.section.pk),
            },
        )
        anchor = getattr(self.subsection_edit_full, "html_id", "")
        expected_redirect = (
            "{}?anchor={}#{}".format(url, anchor, anchor) if anchor else url
        )
        self.assertEqual(response.url, expected_redirect)

    def test_post_updates_variables_and_redirects(self):
        """
        POST with new body content for a 'variables' edit_mode subsection
        should update the subsection 'variables' and redirect back to the section view.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        post_data = {"variable": "Value from writer"}
        response = self.client.post(self.url_variables, data=post_data)
        self.assertEqual(response.status_code, 302)
        url = reverse(
            "composer:writer_section_view",
            kwargs={
                "pk": str(self.instance.pk),
                "section_pk": str(self.section.pk),
            },
        )
        anchor = getattr(self.subsection_edit_variables, "html_id", "")
        expected_redirect = (
            "{}?anchor={}#{}".format(url, anchor, anchor) if anchor else url
        )
        self.assertEqual(response.url, expected_redirect)
        self.subsection_edit_variables.refresh_from_db()
        variable = self.subsection_edit_variables.get_variables().get("variable", {})
        variable_value = variable.get("value", "")
        self.assertEqual(variable_value, "Value from writer")

    def test_post_updates_optional_locked_subsection_and_redirects(self):
        """
        POST to an optional 'locked' edit_mode subsection should update
        the body and redirect back to the section view.
        """
        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.post(self.url_optional, data={"hidden": True})
        self.assertEqual(response.status_code, 302)

        url = reverse(
            "composer:writer_section_view",
            kwargs={
                "pk": str(self.instance.pk),
                "section_pk": str(self.section.pk),
            },
        )
        anchor = getattr(self.subsection_optional, "html_id", "")
        expected_redirect = (
            "{}?anchor={}#{}".format(url, anchor, anchor) if anchor else url
        )
        self.assertEqual(response.url, expected_redirect)

        self.subsection_optional.refresh_from_db()
        self.assertEqual(self.subsection_optional.hidden, True)

    def test_first_get_marks_status_viewed(self):
        """
        First GET should mark a 'default' subsection as 'viewed'.
        """
        self.assertEqual(self.subsection_edit_full.status, "default")

        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url_full)

        self.assertEqual(response.status_code, 200)
        self.subsection_edit_full.refresh_from_db()
        self.assertEqual(self.subsection_edit_full.status, "viewed")

    def test_get_does_not_downgrade_done_status(self):
        """
        GET should not change status if it's already 'done'.
        """
        self.subsection_edit_full.status = "done"
        self.subsection_edit_full.save()

        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.get(self.url_full)

        self.assertEqual(response.status_code, 200)
        self.subsection_edit_full.refresh_from_db()
        self.assertEqual(self.subsection_edit_full.status, "done")

    def test_post_without_done_checkbox_sets_status_viewed(self):
        """
        POST without subsection_done should leave status as 'viewed'.
        If it was 'default', it effectively becomes 'viewed'.
        """
        self.subsection_edit_full.status = "default"
        self.subsection_edit_full.save()

        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.post(self.url_full, data={"body": "Updated body"})

        self.assertEqual(response.status_code, 302)
        self.subsection_edit_full.refresh_from_db()
        self.assertEqual(self.subsection_edit_full.status, "viewed")

    def test_post_with_done_checkbox_sets_status_done(self):
        """
        POST with subsection_done checked should set status to 'done'.
        """
        self.subsection_edit_full.status = "default"
        self.subsection_edit_full.save()

        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.post(
            self.url_full,
            data={
                "body": "Updated body",
                "subsection_done": "1",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.subsection_edit_full.refresh_from_db()
        self.assertEqual(self.subsection_edit_full.status, "done")

    def test_post_can_toggle_done_back_to_viewed(self):
        """
        If status is 'done' and the checkbox is not checked, POST should set status to 'viewed'.
        """
        self.subsection_edit_full.status = "done"
        self.subsection_edit_full.save()

        self.client.login(email="acf@example.com", password="testpass123")
        response = self.client.post(
            self.url_full,
            data={
                "body": "Updated again",
                # no subsection_done → unchecked
            },
        )

        self.assertEqual(response.status_code, 302)
        self.subsection_edit_full.refresh_from_db()
        self.assertEqual(self.subsection_edit_full.status, "viewed")


class WriterInstancePreviewViewTests(BaseWriterViewTests):
    def setUp(self):
        super().setUp()

        # Use the helper to create an ACF parent guide
        self.parent_guide = self.create_acf_parent_guide()

        # Create a ContentGuideInstance in the same group/opdiv
        self.instance = ContentGuideInstance.objects.create(
            title="ACF Draft NOFO",
            opdiv="acf",
            group="acf",
            parent=self.parent_guide,
            status="draft",
            short_name="ACF Draft NOFO (short)",
        )

        # Attach a section + subsection to the *instance* using shared models
        self.section = ContentGuideSection.objects.create(
            content_guide_instance=self.instance,
            order=1,
            name="Instance Section 1",
            html_id="inst-sec-1",
        )
        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Instance Subsection 1",
            tag="h3",
            body="Instance body",
        )

        self.url = reverse(
            "composer:writer_preview",
            kwargs={"pk": self.instance.pk},
        )

    def test_anonymous_user_is_redirected_to_login(self):
        """Anonymous users should be redirected to the login page."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)

    def test_logged_in_writer_can_view_preview_page(self):
        """
        A logged-in writer can view the instance preview, with 2-column layout and buttons.
        """
        self.login_as(self.acf_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Document and preview context
        self.assertEqual(response.context["document"].pk, self.instance.pk)
        self.assertTrue(response.context["is_preview"])
        self.assertIsNotNone(response.context["sections"])

        # Layout and button flags for instances
        self.assertTrue(response.context["show_side_nav"])
        self.assertTrue(response.context["show_save_exit_button"])
        self.assertTrue(response.context["show_download_button"])

        # Optional sanity check if your template has this copy
        self.assertContains(response, "Steps in this NOFO")

        # Make sure we are NOT showing any publish/unpublish UI
        self.assertNotContains(response, "Publish")
        self.assertNotContains(response, "Unpublish")

    def test_post_exit_action_redirects_with_message(self):
        """
        Submitting 'exit' should redirect to writer_index, set success heading,
        and include a link back to the instance in the success message.
        """
        self.login_as(self.acf_user)
        resp = self.client.post(self.url, {"action": "exit"}, follow=False)

        # Redirects to writer index
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("composer:writer_index"))

        # Session variable set for success heading
        follow_resp = self.client.get(resp["Location"])
        self.assertEqual(
            follow_resp.context["success_heading"],
            "Draft NOFO saved",
        )

        # Success message was added, with link to writer_instance_redirect
        msgs = list(get_messages(resp.wsgi_request))
        redirect_link = reverse(
            "composer:writer_instance_redirect",
            kwargs={"pk": self.instance.pk},
        )
        expected_fragment = f'You saved: “<a href="{redirect_link}">'
        self.assertTrue(
            any(expected_fragment in str(m) for m in msgs),
            f"Expected to find {expected_fragment!r} in messages, got: {msgs!r}",
        )

    def test_hidden_and_variable_subsections_render_correctly(self):
        """
        Writer preview should:
        - Skip hidden subsections entirely
        - Render variable placeholders and mark only those with values
          using 'md-curly-variable--value'.
        """
        self.login_as(self.acf_user)

        # Normal subsection (full edit)
        normal_subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=10,
            name="Normal subsection",
            tag="h3",
            body="Normal body",
            edit_mode="full",
        )

        # Variables subsection: 3 placeholders, 2 variables defined in JSON, but only 1 has a value
        variables_body = (
            "Opportunity name: {Insert opportunity name.}\n\n"
            "Opportunity number: {Insert opportunity number.}\n\n"
            "Assistance listing: {Insert assistance listing number.}\n"
        )
        variables_subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=20,
            name="Variables subsection",
            tag="h3",
            body=variables_body,
            edit_mode="variables",
        )

        # Two variables defined, but only one has a 'value'
        variables_subsection.variables = json.dumps(
            {
                "insert_opportunity_name": {
                    "key": "insert_opportunity_name",
                    "type": "string",
                    "label": "Insert opportunity name.",
                    "value": "NOFO 5000 deluxe",
                },
                "insert_opportunity_number": {
                    "key": "insert_opportunity_number",
                    "type": "string",
                    "label": "Insert opportunity number.",
                    # no value
                },
                # Note: third placeholder ("Insert assistance listing number.") has no entry
            }
        )
        variables_subsection.save()

        # Hidden subsection: should not appear in preview at all
        hidden_subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=30,
            name="Hidden subsection",
            tag="h3",
            body="<p>Should not appear</p>",
            optional=True,
            hidden=True,
        )

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()

        # Hidden heading should NOT appear
        self.assertNotIn(hidden_subsection.name, html)
        self.assertNotIn(hidden_subsection.body, html)

        # Normal + variables headings should appear
        self.assertIn(normal_subsection.name, html)
        self.assertIn(normal_subsection.body, html)
        self.assertIn(variables_subsection.name, html)

        # 3 "md-curly-variable" spans, but only one has the '--value' class
        self.assertEqual(html.count('<span class="md-curly-variable'), 3)
        self.assertEqual(
            html.count('<span class="md-curly-variable md-curly-variable--value'), 1
        )

    def test_post_unknown_action_returns_400(self):
        self.login_as(self.acf_user)
        resp = self.client.post(self.url, {"action": "bogus"}, follow=False)
        self.assertEqual(resp.status_code, 400)
