# Security policy

QATrack+ is used by radiation therapy and diagnostic imaging clinics, so we
take security reports seriously and are grateful to anyone who takes the time
to send one. Thank you for helping keep clinics and their patients safe.

## Reporting a vulnerability

**Please don't report security vulnerabilities in public GitHub issues,
discussions, pull requests or the Google Group.** A public report gives
everyone the details before there is a fix that clinics can install.

Instead, report it privately in one of these ways:

- **GitHub private vulnerability reporting.** If the repository's
  [Security tab](https://github.com/qatrackplus/qatrackplus/security) shows a
  **Report a vulnerability** button, use it. Your report is visible only to you
  and the maintainers, and we can work on a fix together in a private advisory.
- **Email** the maintainer at
  [medphys@crcrewso.ca](mailto:medphys@crcrewso.ca), with "QATrack+ security"
  in the subject line.

It helps a lot if your report includes:

- the QATrack+ version (`Admin › About`), and how it is deployed (Linux,
  Windows, Docker) and on which database;
- what the problem is and what an attacker could do with it — for example,
  which kind of user (anonymous, any signed-in user, a user without a given
  permission) can reach it;
- steps to reproduce it, or a proof of concept;
- any fix or workaround you have in mind.

You don't need to have everything worked out before writing to us. A partial
report is far better than none.

## What happens next

QATrack+ is maintained by volunteers, so we can't promise fixed response times,
but we will:

- let you know we've received your report;
- keep you updated as we confirm the problem and work on a fix;
- agree with you on when the details are made public, normally once a fixed
  release is available;
- credit you in the release notes and advisory, if you'd like to be credited.

Please give us a reasonable chance to release a fix before sharing the details
with anyone else.

## Supported versions

Security fixes are made for the latest QATrack+ release, and published as a
new patch release (for example, 4.0.x).

| Version | Receives security fixes |
| ------- | ----------------------- |
| 4.0.x   | Yes                     |
| < 4.0   | No                      |

If you're running an older version, the fix is to upgrade. The
[upgrade guides](https://docs.qatrackplus.com/en/stable/) explain how.

## Scope

QATrack+ is designed to run on a clinic's internal network, not to be exposed
directly to the internet (see the [README](README.md)). That shapes what we
treat as a vulnerability, but it doesn't make internal-only problems
unimportant: a flaw that lets a signed-in user see or change data they
shouldn't is exactly the kind of thing we want to hear about.

If you're unsure whether something counts, report it privately anyway. We'd
much rather hear about something that turns out to be harmless than miss
something that matters.
