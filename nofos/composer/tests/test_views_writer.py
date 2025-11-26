from composer.models import ContentGuide, ContentGuideInstance
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class WriterDashboardViewTests(TestCase):
    def setUp(self):
        # Two users: bloom (super group) and a regular opdiv user
        self.bloom_user = User.objects.create_user(
            email="bloom@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.acf_user = User.objects.create_user(
            email="acf@example.com",
            password="testpass123",
            group="acf",
            force_password_reset=False,
        )

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

    def test_non_bloom_user_sees_only_their_group_instances_and_guides(self):
        """
        A non-bloom user only sees ContentGuideInstances and ContentGuides
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
            status="active",
        )
        hrsa_guide = ContentGuide.objects.create(
            title="HRSA Content Guide",
            opdiv="hrsa",
            group="hrsa",
            status="active",
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

    def test_bloom_user_sees_all_groups_instances_and_guides(self):
        """
        A bloom user can see ALL groups' ContentGuideInstances and ContentGuides.
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
            status="active",
        )
        hrsa_guide = ContentGuide.objects.create(
            title="HRSA Content Guide",
            opdiv="hrsa",
            group="hrsa",
            status="active",
        )

        self.client.login(email="bloom@example.com", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        draft_nofos = set(response.context["draft_nofos"])
        content_guides = set(response.context["content_guides"])

        self.assertEqual(draft_nofos, {acf_instance, hrsa_instance})
        self.assertEqual(content_guides, {acf_guide, hrsa_guide})


class WriterInstanceStartViewTests(TestCase):
    def setUp(self):
        self.bloom_user = User.objects.create_user(
            email="bloom@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.acf_user = User.objects.create_user(
            email="acf@example.com",
            password="testpass123",
            group="acf",
            force_password_reset=False,
        )
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
            status="active",
        )
        hrsa_guide = ContentGuide.objects.create(
            title="HRSA Guide",
            opdiv="hrsa",
            group="hrsa",
            status="active",
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
            status="active",
        )
        hrsa_guide = ContentGuide.objects.create(
            title="HRSA Guide",
            opdiv="hrsa",
            group="hrsa",
            status="active",
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
            status="active",
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


class WriterInstanceDetailsViewTests(TestCase):
    def setUp(self):
        # Users
        self.acf_user = User.objects.create_user(
            email="acf@example.com",
            password="testpass123",
            group="acf",
            force_password_reset=False,
        )
        self.hrsa_user = User.objects.create_user(
            email="hrsa@example.com",
            password="testpass123",
            group="hrsa",
            force_password_reset=False,
        )
        self.bloom_user = User.objects.create_user(
            email="bloom@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )

        # Parent content guide (ACF)
        self.parent_guide = ContentGuide.objects.create(
            title="ACF Core Content Guide",
            opdiv="acf",
            group="acf",
            status="active",
        )

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
        # Should redirect to writer_index
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("composer:writer_index"))

        # Instance was created
        instance = ContentGuideInstance.objects.get(title="My First Draft NOFO")
        self.assertEqual(instance.parent, self.parent_guide)
        self.assertEqual(instance.group, "acf")
        self.assertEqual(instance.opdiv, "acf")
        self.assertEqual(instance.agency, "Some ACF Office")
        self.assertEqual(instance.short_name, "First Draft")
        self.assertEqual(instance.number, "ACF-123")

        # Success message present
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("Draft NOFO “First Draft” created successfully." in m for m in messages)
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
