from composer.conditional.conditional_questions import CONDITIONAL_QUESTIONS
from composer.models import ContentGuide, ContentGuideInstance
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
