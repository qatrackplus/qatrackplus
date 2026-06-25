from django import forms
from django.test import TestCase

from qatrack.qatrack_core.forms import BetterFormMixin


class DummyForm(BetterFormMixin, forms.Form):
    """A test form with fieldsets."""
    name = forms.CharField()
    age = forms.IntegerField()
    email = forms.EmailField()

    fieldsets = [
        (
            'personal', {
                'fields': ['name', 'age'],
                'legend': 'Personal Information',
                'classes': ['personal-info'],
                'description': 'Your personal details',
            }
        ),
        ('contact', {
            'fields': ['email'],
        }),
    ]


class BetterFormMixinTest(TestCase):
    """Test the BetterFormMixin functionality."""

    def setUp(self):
        self.form = DummyForm()

    def test_get_fieldsets(self):
        """Test that get_fieldsets returns the correct structure."""
        fieldsets = self.form.get_fieldsets()
        self.assertEqual(len(fieldsets), 2)

        # Test personal fieldset
        name, options = fieldsets[0]
        self.assertEqual(name, 'personal')
        self.assertEqual(options['fields'], ['name', 'age'])
        self.assertEqual(options['legend'], 'Personal Information')
        self.assertEqual(options['classes'], 'personal-info')
        self.assertEqual(options['description'], 'Your personal details')

        # Test contact fieldset
        name, options = fieldsets[1]
        self.assertEqual(name, 'contact')
        self.assertEqual(options['fields'], ['email'])
        self.assertEqual(options['legend'], 'Contact')
        self.assertEqual(options['classes'], '')
        self.assertEqual(options['description'], '')

    def test_as_fieldset(self):
        """Test that as_fieldset renders the correct HTML."""
        html = self.form.as_fieldset()

        # Check for fieldset elements
        self.assertIn('<fieldset class="personal-info">', html)
        self.assertIn('<legend>Personal Information</legend>', html)
        self.assertIn('<p class="description">Your personal details</p>', html)

        # Check for form fields
        self.assertIn('name="name"', html)
        self.assertIn('name="age"', html)
        self.assertIn('name="email"', html)

    def test_fieldset_attribute_access(self):
        """Test that fieldsets can be accessed as attributes by name."""
        self.assertTrue(hasattr(self.form.fieldsets, 'personal'))
        
        # Test attribute access
        personal_fs = self.form.fieldsets.personal
        self.assertEqual(personal_fs.name, 'personal')
        self.assertEqual(personal_fs.legend, 'Personal Information')
        
        # Test item access
        contact_fs = self.form.fieldsets['contact']
        self.assertEqual(contact_fs.name, 'contact')
        
        # Test iteration over fieldset yields bound fields
        personal_fields = list(personal_fs)
        self.assertEqual(len(personal_fields), 2)
        self.assertEqual(personal_fields[0].name, 'name')
        self.assertEqual(personal_fields[1].name, 'age')

    def test_no_fieldsets(self):
        """Test form without fieldsets defined."""

        class NoFieldsetsForm(BetterFormMixin, forms.Form):
            name = forms.CharField()

        form = NoFieldsetsForm()
        fieldsets = form.get_fieldsets()

        self.assertEqual(len(fieldsets), 1)
        name, options = fieldsets[0]
        self.assertIsNone(name)
        self.assertEqual(options['fields'], ['name'])

    def test_missing_field(self):
        """Test that fieldsets handle missing fields gracefully."""

        class MissingFieldForm(BetterFormMixin, forms.Form):
            name = forms.CharField()
            fieldsets = [
                ('test', {
                    'fields': ['name', 'nonexistent_field'],
                }),
            ]

        form = MissingFieldForm()
        fieldsets = form.get_fieldsets()

        self.assertEqual(len(fieldsets), 1)
        name, options = fieldsets[0]
        self.assertEqual(options['fields'], ['name'])  # nonexistent_field should be filtered out
