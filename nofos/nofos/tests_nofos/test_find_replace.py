from django.test import TestCase
from django.urls import reverse
from ..models import Nofo, Section, Subsection
from users.models import BloomUser

class FindReplaceTests(TestCase):
    def setUp(self):
        # Create test user and log in
        self.user = BloomUser.objects.create_user(
            email="test@example.com", 
            password="testpass123",
            group="bloom",
            force_password_reset=False
        )
        self.client.force_login(self.user)

        # Create test NOFO structure
        self.nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="Test",
            opdiv="Test OpDiv",
            status="draft"
        )
        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Test Section",
            order=1,
            html_id="test-section"
        )
        self.subsection1 = Subsection.objects.create(
            section=self.section,
            name="Test Subsection 1",
            body="This is a test document with some test content.",
            order=1,
            tag="h3"
        )
        self.subsection2 = Subsection.objects.create(
            section=self.section,
            name="Test Subsection 2",
            body="Another test document with different content.",
            order=2,
            tag="h3"
        )

    def test_find_replace_basic_flow(self):
        """Test the basic find & replace functionality"""
        url = reverse('nofos:nofo_find_replace', kwargs={'pk': self.nofo.id})

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'nofos/nofo_find_replace.html')

        # Test find with matches
        response = self.client.post(url, {
            'action': 'find',
            'find_text': 'test',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['subsection_matches']), 2)

        # Test find with no matches
        response = self.client.post(url, {
            'action': 'find',
            'find_text': 'nonexistent',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No matches found')

        # Test replace with selection
        response = self.client.post(url, {
            'action': 'replace',
            'find_text': 'test',
            'replace_text': 'example',
            'replace_subsections': [str(self.subsection1.id)],
        }, follow=True)

        self.subsection1.refresh_from_db()
        self.subsection2.refresh_from_db()
        self.assertIn('example', self.subsection1.body)
        self.assertIn('test', self.subsection2.body)

    def test_validation_cases(self):
        """Test various validation scenarios"""
        url = reverse('nofos:nofo_find_replace', kwargs={'pk': self.nofo.id})

        # Test empty find text
        response = self.client.post(url, {
            'action': 'find',
            'find_text': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('subsection_matches', response.context)

        # Test replace without selection
        response = self.client.post(url, {
            'action': 'replace',
            'find_text': 'test',
            'replace_text': 'example',
        }, follow=True)
        self.assertRedirects(response, reverse('nofos:nofo_edit', kwargs={'pk': self.nofo.id}))

        # Test replace without replace text when subsections selected
        response = self.client.post(url, {
            'action': 'replace',
            'find_text': 'test',
            'replace_text': '',
            'replace_subsections': [str(self.subsection1.id)],
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'nofos/nofo_find_replace.html')

    def test_complex_replacements(self):
        """Test various complex replacement scenarios"""
        test_cases = [
            # Case sensitivity
            ("Test TEST test", "test", "new", "new new new"),
            # HTML content
            ("<p>Test</p><p>Test</p>", "Test", "New", "<p>New</p><p>New</p>"),
            # Special characters
            ("test.com", ".", "dot", "testdotcom"),
            # Whitespace handling
            ("  test  test  ", "test", "new", "  new  new  "),
            # Multiline content
            ("test\ntest", "test", "new", "new\nnew"),
        ]

        url = reverse('nofos:nofo_find_replace', kwargs={'pk': self.nofo.id})

        for original, find, replace, expected in test_cases:
            self.subsection1.body = original
            self.subsection1.save()

            response = self.client.post(url, {
                'action': 'replace',
                'find_text': find,
                'replace_text': replace,
                'replace_subsections': [str(self.subsection1.id)],
            }, follow=True)

            self.subsection1.refresh_from_db()
            self.assertEqual(self.subsection1.body, expected)
