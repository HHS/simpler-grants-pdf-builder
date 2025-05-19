from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from nofos.models import Nofo, Section, Subsection
from users.models import BloomUser


class NofoRemovePagebreaksViewTest(TestCase):
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
        
        response = self.client.get(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pagebreak_count'], 6)  # 3 markdown + 1 HTML + 2 CSS

    def test_post_removes_all_pagebreaks(self):
        """Test that POST request removes all types of pagebreaks"""
        subsection = self.create_subsection_with_pagebreaks()
        
        response = self.client.post(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
        
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
        
        response = self.client.post(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "1 pagebreak has been removed.")

    def test_success_message_multiple_pagebreaks(self):
        """Test that correct success message is shown when removing multiple pagebreaks"""
        subsection = self.create_subsection_with_pagebreaks()
        
        response = self.client.post(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "6 pagebreaks have been removed.")

    def test_archived_nofo_access_denied(self):
        """Test that archived NOFOs cannot be accessed"""
        self.nofo.archived = "2025-05-19"
        self.nofo.save()
        
        response = self.client.get(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.status_code, 400)
        
        response = self.client.post(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.status_code, 400)

    def test_cancelled_nofo_access_denied(self):
        """Test that cancelled NOFOs cannot be accessed"""
        self.nofo.status = 'cancelled'
        self.nofo.save()
        
        response = self.client.get(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.status_code, 400)
        
        response = self.client.post(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
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
        response = self.client.get(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
        self.assertEqual(response.context['pagebreak_count'], 0)
        
        # Check that post still works and shows appropriate message
        response = self.client.post(reverse('nofos:nofo_remove_pagebreaks', kwargs={'pk': self.nofo.pk}))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "0 pagebreaks have been removed.")
