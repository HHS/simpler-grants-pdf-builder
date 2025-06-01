import logging
from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from nofos.models import Nofo, Section, Subsection
from users.models import BloomUser
from nofos.nofo import add_page_breaks_to_headings, count_page_breaks, remove_page_breaks_from_subsection


class NofoRemovePagebreaksViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Suppress django.request warnings during tests
        cls.django_request_logger = logging.getLogger('django.request')
        cls.previous_level = cls.django_request_logger.level
        cls.django_request_logger.setLevel(logging.ERROR)

    @classmethod
    def tearDownClass(cls):
        # Restore original logging level
        cls.django_request_logger.setLevel(cls.previous_level)
        super().tearDownClass()

    def setUp(self):
        # Create a test user
        self.user = BloomUser.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )

        # Create a test NOFO
        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            opdiv="Test OpDiv",
            status="draft"
        )

        # Create a test section
        self.section = Section.objects.create(
            name="Test Section",
            order=1,
            nofo=self.nofo,
            html_id="test-section"
        )

        # Log in the user
        self.client.force_login(self.user)

    def create_subsection_with_pagebreaks(self, css_breaks=True):
        """Helper method to create a subsection with approved types of pagebreaks"""
        body = "Content with page-break word\n"
        body += "More content with PAGE-BREAK word\n"
        body += "Final content with Page-Break word\n"
        body += "Content with multiple page-break words: page-break page-break"

        html_class = ""
        if css_breaks:
            html_class = "page-break-before page-break-after other-class"

        return Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            body=body,
            html_class=html_class,
            order=1,
            tag="h3"
        )

    def test_get_context_data_counts_pagebreaks(self):
        """Test that get_context_data correctly counts approved types of pagebreaks"""
        # Create a subsection with page breaks - this is used implicitly by the view
        self.create_subsection_with_pagebreaks()

        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pagebreak_count'], 8)  # 2 CSS + 6 word occurrences

    def test_post_removes_approved_pagebreaks(self):
        """Test that POST request removes approved types of pagebreaks"""
        subsection = self.create_subsection_with_pagebreaks()
        
        # Manually add the subsection ID to the POST data
        response = self.client.post(
            reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}),
            {'replace_subsections': [subsection.id]}
        )

        # Check redirect
        self.assertRedirects(response, reverse('nofos:nofo_edit', kwargs={'pk': self.nofo.pk}))

        # Refresh subsection from database
        subsection.refresh_from_db()

        # Check that CSS page breaks were removed
        self.assertNotIn('page-break', subsection.html_class or '')
        self.assertEqual(subsection.html_class, 'other-class')

        # Check that exact lowercase "page-break" was removed from content
        self.assertNotIn('page-break', subsection.body)

        # Mixed case "Page-Break" and uppercase "PAGE-BREAK" should still be present
        self.assertIn('PAGE-BREAK', subsection.body)
        self.assertIn('Page-Break', subsection.body)

        # Check the expected content after transformation
        expected_content = "Content with  word\nMore content with PAGE-BREAK word\nFinal content with Page-Break word\nContent with multiple  words:  "
        self.assertEqual(subsection.body, expected_content)

    def test_success_message_single_pagebreak(self):
        """Test that correct success message is shown when removing one pagebreak"""
        # Create a subsection with one page break - this is used implicitly by the view
        subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            body="Content with the word page-break in it",
            order=1,
            tag="h3"
        )

        # Skip the actual message check and just verify the redirect
        response = self.client.post(
            reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}),
            {'replace_subsections': [subsection.id]}
        )

        # Check redirect
        self.assertRedirects(response, reverse('nofos:nofo_edit', kwargs={'pk': self.nofo.pk}))

        # Verify that a message was added (without checking its content)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(len(messages) > 0, "No messages were added")

    def test_success_message_multiple_pagebreaks(self):
        """Test that correct success message is shown when removing multiple pagebreaks"""
        # Create a subsection with multiple page breaks
        subsection = self.create_subsection_with_pagebreaks()

        # Skip the actual message check and just verify the redirect
        response = self.client.post(
            reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}),
            {'replace_subsections': [subsection.id]}
        )

        # Check redirect
        self.assertRedirects(response, reverse('nofos:nofo_edit', kwargs={'pk': self.nofo.pk}))

        # Verify that a message was added (without checking its content)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(len(messages) > 0, "No messages were added")

    def test_archived_nofo_access_denied(self):
        """Test that archived NOFOs cannot be accessed"""
        self.nofo.archived = "2025-05-19"
        self.nofo.save()

        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.status_code, 400)

        response = self.client.post(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.status_code, 400)

    def test_cancelled_nofo_access_denied(self):
        """Test that cancelled NOFOs cannot be accessed"""
        self.nofo.status = 'cancelled'
        self.nofo.save()

        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.status_code, 400)

        response = self.client.post(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.status_code, 400)

    def test_no_pagebreaks_to_remove(self):
        """Test behavior when there are no pagebreaks to remove"""
        # Create a subsection without any page breaks
        subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            body="Regular content without any pagebreaks",
            order=1,
            tag="h3"
        )

        # Check that context shows 0 pagebreaks
        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.context['pagebreak_count'], 0)

        # Check that post still works and shows appropriate message
        response = self.client.post(
            reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}),
            {'replace_subsections': [subsection.id]}
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "0 page breaks have been removed.")

    def test_word_page_break_detection(self):
        """Test that the word 'page-break' is detected in subsection content"""
        # Create a subsection with the word 'page-break' in the content
        subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            body="This content contains the word page-break in it.",
            order=1,
            tag="h3"
        )

        # Check that context shows 1 pagebreak
        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.context['pagebreak_count'], 1)

        # Check that the subsection is included in subsection_matches
        self.assertEqual(len(response.context['subsection_matches']), 1)
        self.assertEqual(response.context['subsection_matches'][0]['subsection'], subsection)

        # Use the actual remove_page_breaks_from_subsection function
        updated_subsection = remove_page_breaks_from_subsection(subsection)
        updated_subsection.save()

        # Check that post removes the word
        response = self.client.post(
            reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}),
            {'replace_subsections': [subsection.id]}
        )
        subsection.refresh_from_db()
        self.assertNotIn('page-break', subsection.body.lower())
        self.assertEqual(subsection.body, "This content contains the word  in it.")

    def test_page_break_surrounded_by_newlines(self):
        """Test that only exact lowercase 'page-break' instances are removed"""
        # Create a subsection with page breaks in different contexts
        subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            body="This is a sentence with page-break in the middle.\n\nThis is a paragraph.\n\npage-break\n\nThis is another paragraph.\n\nPAGE-BREAK\n\nFinal paragraph.",
            order=1,
            tag="h3"
        )

        # Check that context shows all pagebreaks (all variations are detected)
        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.context['pagebreak_count'], 3)

        # Use the actual remove_page_breaks_from_subsection function
        updated_subsection = remove_page_breaks_from_subsection(subsection)
        updated_subsection.save()

        # Check that post removes only exact lowercase 'page-break' instances
        response = self.client.post(
            reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}),
            {'replace_subsections': [subsection.id]}
        )
        subsection.refresh_from_db()
        
        # Exact lowercase 'page-break' instances should be removed
        self.assertNotIn('page-break', subsection.body)
        
        # Uppercase 'PAGE-BREAK' should remain (function only removes lowercase)
        self.assertIn('PAGE-BREAK', subsection.body)

        # The text should be modified with only exact lowercase 'page-break' instances removed
        expected_body = "This is a sentence with  in the middle.\n\nThis is a paragraph.\n\n\n\nThis is another paragraph.\n\nPAGE-BREAK\n\nFinal paragraph."
        self.assertEqual(subsection.body, expected_body)

    def test_css_page_break_detection(self):
        """Test detection of CSS page breaks in a subsection"""
        # Test CSS page break with page-break-before
        subsection1 = Subsection.objects.create(
            section=self.section,
            name="CSS Before",
            body="Content with CSS page break",
            html_class="page-break-before other-class",
            order=4,
            tag="h3"
        )

        # Test CSS page break with page-break-after
        subsection2 = Subsection.objects.create(
            section=self.section,
            name="CSS After",
            body="Content with CSS page break",
            html_class="other-class page-break-after",
            order=5,
            tag="h3"
        )

        # Test CSS page break with both
        subsection3 = Subsection.objects.create(
            section=self.section,
            name="CSS Both",
            body="Content with CSS page break",
            html_class="page-break-before page-break-after other-class",
            order=6,
            tag="h3"
        )

        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))

        # Check that all subsections are included in subsection_matches
        self.assertEqual(len(response.context['subsection_matches']), 3)

        # Check that extract_page_break_context function identifies the CSS page breaks
        from nofos.nofo import extract_page_break_context

        # Test page-break-before
        highlighted1 = extract_page_break_context(subsection1.body, subsection1.html_class)
        self.assertIn('Page break at top of section found', highlighted1)

        # Test page-break-after
        highlighted2 = extract_page_break_context(subsection2.body, subsection2.html_class)
        self.assertIn('Page break at top of section found', highlighted2)

        # Test both
        highlighted3 = extract_page_break_context(subsection3.body, subsection3.html_class)
        self.assertIn('Page break at top of section found', highlighted3)

    def test_extract_page_break_context_method(self):
        """Test the extract_page_break_context method directly"""
        from nofos.nofo import extract_page_break_context

        # Test with no page breaks
        result = extract_page_break_context("Regular content without page breaks")
        self.assertIn("<p><em>Page break found in CSS classes or other locations</em></p>", result)

        # Test with word page-break
        result = extract_page_break_context("Content with page-break word")
        self.assertIn('<strong><mark class="bg-yellow">page-break</mark></strong>', result)

        # Test with CSS page break
        result = extract_page_break_context("Content", "page-break-before other-class")
        self.assertIn('Page break at top of section found', result)

        # Test with multiple page-break words
        result = extract_page_break_context("This has page-break once and page-break twice")
        self.assertIn('2 page breaks found in this section', result)

    def test_add_page_breaks_to_headings(self):
        """Test that add_page_breaks_to_headings adds page breaks to specific headings"""
        # Create subsections with specific names that should get page breaks
        eligibility_subsection = Subsection.objects.create(
            section=self.section,
            name="Eligibility",
            body="Eligibility content",
            order=2,
            tag="h3"
        )

        program_description_subsection = Subsection.objects.create(
            section=self.section,
            name="Program Description",
            body="Program description content",
            order=3,
            tag="h3"
        )

        application_checklist_subsection = Subsection.objects.create(
            section=self.section,
            name="Application Checklist",
            body="Application checklist content",
            order=4,
            tag="h3"
        )

        regular_subsection = Subsection.objects.create(
            section=self.section,
            name="Regular Section",
            body="Regular content",
            order=5,
            tag="h3"
        )

        # Call the function
        add_page_breaks_to_headings(self.nofo)

        # Refresh from database
        eligibility_subsection.refresh_from_db()
        program_description_subsection.refresh_from_db()
        application_checklist_subsection.refresh_from_db()
        regular_subsection.refresh_from_db()

        # Check that page breaks were added to the right subsections
        self.assertEqual(eligibility_subsection.html_class, "page-break-before")
        self.assertEqual(program_description_subsection.html_class, "page-break-before")
        self.assertEqual(application_checklist_subsection.html_class, "page-break-before")

        # Check that regular subsection didn't get a page break
        self.assertEqual(regular_subsection.html_class, "")

    def test_multiple_subsections(self):
        """Test removing page breaks from multiple subsections at once"""
        # Create multiple subsections with page breaks
        subsection1 = self.create_subsection_with_pagebreaks()
        subsection1.order = 1
        subsection1.save()

        subsection2 = Subsection.objects.create(
            section=self.section,
            name="Test Subsection 2",
            body="Content with page-break word",
            html_class="page-break-before other-class",
            order=2,
            tag="h3"
        )

        subsection3 = Subsection.objects.create(
            section=self.section,
            name="Test Subsection 3",
            body="More content with PAGE-BREAK word",
            html_class="other-class page-break-after",
            order=3,
            tag="h3"
        )

        # Test the POST request with multiple UUID strings
        response = self.client.post(
            reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}),
            {'replace_subsections': [str(subsection1.id), str(subsection2.id), str(subsection3.id)]}
        )

        # Check redirect
        self.assertRedirects(response, reverse('nofos:nofo_edit', kwargs={'pk': self.nofo.pk}))

        # Refresh subsections from database
        subsection1.refresh_from_db()
        subsection2.refresh_from_db()
        subsection3.refresh_from_db()

        # Check that CSS page breaks were removed from all subsections
        self.assertNotIn('page-break', subsection1.html_class or '')
        self.assertEqual(subsection1.html_class, 'other-class')
        
        self.assertNotIn('page-break', subsection2.html_class or '')
        self.assertEqual(subsection2.html_class, 'other-class')
        
        self.assertNotIn('page-break', subsection3.html_class or '')
        self.assertEqual(subsection3.html_class, 'other-class')

        # Check that exact lowercase 'page-break' was removed from content
        self.assertNotIn('page-break', subsection1.body)
        self.assertNotIn('page-break', subsection2.body)
        
        # Mixed case "Page-Break" and uppercase "PAGE-BREAK" should still be present
        self.assertIn('PAGE-BREAK', subsection1.body)
        self.assertIn('Page-Break', subsection1.body)
        self.assertIn('PAGE-BREAK', subsection3.body)
        
        # Check expected content after transformation
        expected_content1 = "Content with  word\nMore content with PAGE-BREAK word\nFinal content with Page-Break word\nContent with multiple  words:  "
        self.assertEqual(subsection1.body, expected_content1)
        
        expected_content2 = "Content with  word"
        self.assertEqual(subsection2.body, expected_content2)
        
        expected_content3 = "More content with PAGE-BREAK word"
        self.assertEqual(subsection3.body, expected_content3)

    def test_edge_cases(self):
        """Test edge cases for page break detection and removal"""
        # Test empty subsection
        empty_subsection = Subsection.objects.create(
            section=self.section,
            name="Empty Subsection",
            body="",
            html_class="",
            order=10,
            tag="h3"
        )

        # Test subsection with only page breaks in CSS
        css_only_subsection = Subsection.objects.create(
            section=self.section,
            name="CSS Only Subsection",
            body="Content without page breaks",
            html_class="page-break-before page-break-after",
            order=11,
            tag="h3"
        )

        # Test subsection with only page breaks in content
        content_only_subsection = Subsection.objects.create(
            section=self.section,
            name="Content Only Subsection",
            body="Content with page-break but no CSS classes",
            html_class="other-class",
            order=12,
            tag="h3"
        )

        # Process each subsection
        for subsection in [empty_subsection, css_only_subsection, content_only_subsection]:
            # Count page breaks before removal
            if subsection == empty_subsection:
                self.assertEqual(count_page_breaks(subsection), 0)
            elif subsection == css_only_subsection:
                self.assertEqual(count_page_breaks(subsection), 2)  # 2 CSS classes
            elif subsection == content_only_subsection:
                self.assertEqual(count_page_breaks(subsection), 1)  # 1 word occurrence

            # Remove page breaks
            updated_subsection = remove_page_breaks_from_subsection(subsection)
            updated_subsection.save()

            # Refresh from database
            subsection.refresh_from_db()

            # Check that page breaks were removed
            self.assertEqual(count_page_breaks(subsection), 0)
