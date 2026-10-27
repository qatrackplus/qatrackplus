"""The startup warning for an AD_CERT_FILE that QATrack+ cannot use.

When libldap cannot use the CA file, every LDAPS sign-in fails with "Unable to
contact LDAP server", which looks like a network fault. The check names the
real cause instead, as a warning only: a sign-in setting must never stop the
site starting.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from django.core import checks as django_checks
from django.test import SimpleTestCase, override_settings

from qatrack.qatrack_core import checks

# Only the PEM markers matter to the check; the body is never parsed.
PEM = b'-----BEGIN CERTIFICATE-----\nMIIBszCCAVmgAwIBAgIUQ0FfdGVzdF9vbmx5\n-----END CERTIFICATE-----\n'

# The first bytes of a DER certificate, as a Windows .cer export often is.
DER = bytes.fromhex('308203a130820289a003020102021400')


class TestAdCertFileCheck(SimpleTestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def write(self, name, contents):
        path = self.dir / name
        path.write_bytes(contents)
        return path

    def run_check(self, value):
        with override_settings(AD_CERT_FILE=value):
            return checks.check_ad_cert_file(None)

    def test_unset_is_silent(self):
        """Most sites never set it, and a public CA needs no file at all."""
        assert self.run_check('') == []
        assert self.run_check(None) == []

    def test_a_readable_pem_file_is_silent(self):
        assert self.run_check(str(self.write('ca.pem', PEM))) == []

    def test_a_bundle_with_several_certificates_is_silent(self):
        """Root plus intermediates, one after the other, as the docs suggest."""
        assert self.run_check(str(self.write('ca.pem', PEM + PEM))) == []

    def test_a_missing_file_warns(self):
        path = self.dir / 'ldap' / 'ca.pem'
        warnings = self.run_check(str(path))
        assert [w.id for w in warnings] == ['qatrack.W011']
        assert str(path) in warnings[0].msg
        assert 'Unable to contact LDAP server' in warnings[0].msg
        assert '/etc/qatrack/ldap/ca.pem' in warnings[0].hint

    def test_a_folder_warns(self):
        """Setting AD_CERT_FILE to the mounted folder rather than the file in it."""
        warnings = self.run_check(str(self.dir))
        assert [w.id for w in warnings] == ['qatrack.W011']
        assert 'folder' in warnings[0].msg

    def test_an_unreadable_file_warns(self):
        path = self.write('ca.pem', PEM)
        with mock.patch.object(Path, 'open', side_effect=PermissionError(13, 'Permission denied')):
            warnings = self.run_check(str(path))
        assert [w.id for w in warnings] == ['qatrack.W012']
        assert 'Permission denied' in warnings[0].msg
        assert 'chmod 644' in warnings[0].hint

    @pytest.mark.skipif(sys.platform == 'win32', reason='POSIX file permissions')
    def test_an_unreadable_file_warns_for_real(self):
        """The mocked test above, against a real file with no read permission."""
        if os.geteuid() == 0:
            pytest.skip('root can read any file')
        path = self.write('ca.pem', PEM)
        path.chmod(0o200)
        self.addCleanup(path.chmod, 0o600)
        assert [w.id for w in self.run_check(str(path))] == ['qatrack.W012']

    def test_a_der_file_warns(self):
        warnings = self.run_check(str(self.write('ca.cer', DER)))
        assert [w.id for w in warnings] == ['qatrack.W013']
        assert 'PEM' in warnings[0].msg
        assert 'openssl x509 -inform der -in ca.cer -out ca.pem' in warnings[0].hint

    def test_a_private_key_is_not_mistaken_for_a_certificate(self):
        key = b'-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----\n'
        assert [w.id for w in self.run_check(str(self.write('ca.pem', key)))] == ['qatrack.W013']

    def test_warnings_never_show_the_file_contents(self):
        marker = b'do-not-print-this-7f3a'
        path = self.write('ca.pem', b'not a certificate ' + marker)
        warnings = self.run_check(str(path))
        assert warnings
        for warning in warnings:
            assert marker.decode() not in warning.msg
            assert marker.decode() not in (warning.hint or '')

    def test_it_is_a_warning_not_an_error(self):
        """System checks run before migrate; an Error would stop the site starting."""
        for value in (str(self.dir / 'missing.pem'), str(self.write('ca.cer', DER))):
            for warning in self.run_check(value):
                assert warning.level == django_checks.WARNING
                assert not warning.is_serious()

    def test_it_runs_with_the_other_system_checks(self):
        with override_settings(AD_CERT_FILE=str(self.dir / 'missing.pem')):
            ids = [m.id for m in django_checks.run_checks()]
        assert 'qatrack.W011' in ids
