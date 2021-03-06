# Generated by Django 2.1.11 on 2020-01-31 15:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qa', '0049_convert_upload_attachments'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='reference',
            options={},
        ),
        migrations.AlterModelOptions(
            name='testlistmembership',
            options={'ordering': ('order',)},
        ),
        migrations.AlterField(
            model_name='test',
            name='calculation_procedure',
            field=models.TextField(blank=True, help_text="For composite, string composite, and upload tests, enter a Python snippet for evaluation of this test.<br/>For other test types, you may enter a Python snippet to set the initial value of this test.  For example, if you want to set an initial default value of 123 that a user can override for a numerical test, you would set your calculation procedure to:<br/><pre>your_test = 123</pre>To set an initial multiple choice value you would use:<pre>your_test = 'some choice'</pre>To set an initial Boolean value you would use:<pre>your_test = True # or False</pre>", null=True),
        ),
        migrations.AlterField(
            model_name='test',
            name='formatting',
            field=models.CharField(blank=True, default='', help_text="Python style string format for numerical results. Leave blank for the QATrack+ default, select one of the predefined options, or enter your own formatting string. <br/>Use e.g. %.2F to display as fixed precision with 2 decimal places, or %.3E to show as scientific format with 3 significant figures, or %.4G to use 'general' formatting with up to 4 significant figures.<br/>You may also use new style Python string formatting (e.g. {:06.2f}).", max_length=10),
        ),
    ]
