import logging
from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from nofos.models import Nofo, Section, Subsection
from users.models import BloomUser


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

    def create_subsection_with_pagebreaks(self, markdown_breaks=True, html_breaks=True, css_breaks=True):
        """Helper method to create a subsection with different types of pagebreaks"""
        body = ""
        html_class = ""
        
        if markdown_breaks:
            body += "Content before\n---\nContent after\n"
            body += "More content\n----\nEven more content\n"
            body += "Final content\n-----\nVery final content"
        
        if html_breaks:
            body += '<div class="page-break--hr--container"><hr class="page-break-before page-break--hr">' + \
                   '<span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div>'
        
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
        """Test that get_context_data correctly counts all types of pagebreaks"""
        subsection = self.create_subsection_with_pagebreaks()
        
        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pagebreak_count'], 11)  # 3 markdown + 1 HTML + 2 CSS + 5 word occurrences

    def test_post_removes_all_pagebreaks(self):
        """Test that POST request removes all types of pagebreaks"""
        subsection = self.create_subsection_with_pagebreaks()
        
        response = self.client.post(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        
        # Check redirect
        self.assertRedirects(response, reverse('nofos:nofo_edit', kwargs={'pk': self.nofo.pk}))
        
        # Refresh subsection from database
        subsection.refresh_from_db()
        
        # Check that pagebreaks were removed
        self.assertNotIn('---', subsection.body)
        self.assertNotIn('----', subsection.body)
        self.assertNotIn('-----', subsection.body)
        self.assertNotIn('page-break--hr--container', subsection.body)
        self.assertNotIn('page-break', subsection.html_class or '')
        self.assertEqual(subsection.html_class, 'other-class')

    def test_success_message_single_pagebreak(self):
        """Test that correct success message is shown when removing one pagebreak"""
        subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            body="Content\n---\nMore content",
            order=1,
            tag="h3"
        )
        
        response = self.client.post(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "1 page break has been removed.")

    def test_success_message_multiple_pagebreaks(self):
        """Test that correct success message is shown when removing multiple pagebreaks"""
        subsection = self.create_subsection_with_pagebreaks()
        
        response = self.client.post(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "11 page breaks have been removed.")

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
        response = self.client.post(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
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
        
        # Check that post removes the word
        response = self.client.post(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        subsection.refresh_from_db()
        self.assertNotIn('page-break', subsection.body.lower())
        self.assertEqual(subsection.body, "This content contains the word  in it.")
    
    def test_case_insensitive_page_break_detection(self):
        """Test that case variations of 'page-break' are detected"""
        # Create a subsection with different case variations
        subsection = Subsection.objects.create(
            section=self.section,
            name="Test Subsection",
            body="PAGE-BREAK at the start, page-break in the middle, and Page-Break at the end.",
            order=1,
            tag="h3"
        )
        
        # Check that context shows 3 pagebreaks
        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.context['pagebreak_count'], 3)
        
        # Check that post removes all variations
        response = self.client.post(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        subsection.refresh_from_db()
        self.assertNotIn('PAGE-BREAK', subsection.body)
        self.assertNotIn('page-break', subsection.body)
        self.assertNotIn('Page-Break', subsection.body)
        
        # The text should be modified with all instances removed
        self.assertEqual(subsection.body, " at the start,  in the middle, and  at the end.")
    
    def test_page_break_at_top_detection(self):
        """Test detection of page breaks at the top of a subsection"""
        # Test markdown page break at top
        subsection1 = Subsection.objects.create(
            section=self.section,
            name="Top Markdown",
            body="\n---\nContent after page break",
            order=2,
            tag="h3"
        )
        
        # Test HTML page break at top
        subsection2 = Subsection.objects.create(
            section=self.section,
            name="Top HTML",
            body='<div class="page-break--hr--container"></div>Content after page break',
            order=3,
            tag="h3"
        )
        
        # Test CSS page break at top
        subsection3 = Subsection.objects.create(
            section=self.section,
            name="Top CSS",
            body="Content with CSS page break",
            html_class="page-break-before other-class",
            order=4,
            tag="h3"
        )
        
        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        
        # Check that all subsections are included in subsection_matches
        self.assertEqual(len(response.context['subsection_matches']), 3)
        
        # Check that extract_page_break_context method identifies these as top page breaks
        view = response.context['view']
        
        # Test markdown page break at top
        highlighted1 = view.extract_page_break_context(subsection1.body)
        self.assertIn('<strong><mark class="bg-yellow">Page break at the top', highlighted1)
        self.assertIn('Markdown', highlighted1)
        
        # Test HTML page break at top
        highlighted2 = view.extract_page_break_context(subsection2.body)
        self.assertIn('<strong><mark class="bg-yellow">Page break at the top', highlighted2)
        self.assertIn('HTML', highlighted2)
        
        # Test CSS page break at top
        highlighted3 = view.extract_page_break_context(subsection3.body, subsection3.html_class)
        self.assertIn('<strong><mark class="bg-yellow">Page break at the top', highlighted3)
        self.assertIn('CSS class', highlighted3)
    
    def test_page_break_at_bottom_detection(self):
        """Test detection of page breaks at the bottom of a subsection"""
        # Test markdown page break at bottom
        subsection1 = Subsection.objects.create(
            section=self.section,
            name="Bottom Markdown",
            body="Content before page break\n---\n",
            order=5,
            tag="h3"
        )
        
        # Test HTML page break at bottom
        subsection2 = Subsection.objects.create(
            section=self.section,
            name="Bottom HTML",
            body='Content before page break<div class="page-break--hr--container"></div>',
            order=6,
            tag="h3"
        )
        
        response = self.client.get(reverse('nofos:nofo_remove_page_breaks', kwargs={'pk': self.nofo.pk}))
        
        # Check that all subsections are included in subsection_matches
        self.assertEqual(len(response.context['subsection_matches']), 2)
        
        # Check that extract_page_break_context method identifies these as bottom page breaks
        view = response.context['view']
        
        # Test markdown page break at bottom
        highlighted1 = view.extract_page_break_context(subsection1.body)
        self.assertIn('<strong><mark class="bg-yellow">Page break at the bottom', highlighted1)
        self.assertIn('Markdown', highlighted1)
        
        # Test HTML page break at bottom
        highlighted2 = view.extract_page_break_context(subsection2.body)
        self.assertIn('<strong><mark class="bg-yellow">Page break at the bottom', highlighted2)
        self.assertIn('HTML', highlighted2)
    
    def test_extract_page_break_context_method(self):
        """Test the extract_page_break_context method directly"""
        from nofos.views import NofoRemovePageBreaksView
        
        view = NofoRemovePageBreaksView()
        
        # Test with no page breaks
        result = view.extract_page_break_context("Regular content without page breaks")
        self.assertIn("<p><em>Page break found in CSS classes or other locations</em></p>", result)
        
        # Test with word page-break
        result = view.extract_page_break_context("Content with page-break word")
        self.assertIn('<strong><mark class="bg-yellow">page-break</mark></strong>', result)
        
        # Test with markdown page break in middle
        result = view.extract_page_break_context("Before\n---\nAfter")
        self.assertIn('<strong><mark class="bg-yellow">Markdown page break found</mark></strong>', result)
        
        # Test with HTML page break in middle
        result = view.extract_page_break_context('Before<div class="page-break--hr--container"><hr class="page-break-before page-break--hr"><span class="page-break--hr--text">[ ↓ page-break ↓ ]</span></div>After')
        self.assertIn('HTML page break', result)
        self.assertIn('<mark class="bg-yellow">page-break</mark>', result)
        
        # Test with page break at top (markdown)
        result = view.extract_page_break_context("\n---\nContent")
        self.assertIn('<strong><mark class="bg-yellow">Page break at the top', result)
        self.assertIn('Markdown', result)
        
        # Test with page break at top (HTML)
        result = view.extract_page_break_context('<div class="page-break--hr--container"></div>Content')
        self.assertIn('<strong><mark class="bg-yellow">Page break at the top', result)
        self.assertIn('HTML', result)
        
        # Test with page break at top (CSS)
        result = view.extract_page_break_context("Content", "page-break-before other-class")
        self.assertIn('<strong><mark class="bg-yellow">Page break at the top', result)
        self.assertIn('CSS class', result)
        
        # Test with page break at bottom (markdown)
        result = view.extract_page_break_context("Content\n---\n")
        self.assertIn('<strong><mark class="bg-yellow">Page break at the bottom', result)
        self.assertIn('Markdown', result)
        
        # Test with page break at bottom (HTML)
        result = view.extract_page_break_context('Content<div class="page-break--hr--container"></div>')
        self.assertIn('<strong><mark class="bg-yellow">Page break at the bottom', result)
        self.assertIn('HTML', result)
