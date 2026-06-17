# Welcome

I would like to welcome you to the QATrack+ main repository. Here I feel I need to start with a personal message. I am attempting to revitalize both the project and the community in a way that balances the user and the developer. Everyone should *feel* welcome. Everyone should ***be*** welcome. I am not perfect and maintaining this project is an honour that I do not have all the skills to match. Please grant me the grace to make mistakes, and, for all here, assume comments come from a good place. There are many here who have only contributed to one FOSS project, there are many for which this might be their only exposure to open source at all. This project is coded in English, and used across at least a dozen nations for which English is not their primary language. Please try to assume all interactions start from a place of respect and a desire to help.

To start, I would like to specifically point out two changes as we move this project forward.

- Licensing: starting with version 4.0, this project will switch to [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0.html) ([Wiki](https://en.wikipedia.org/wiki/Apache_License)), aligning with many of the tools QATrack+ relies on. Until then, the current license remains MIT. The license holder remains with the Ottawa Cancer Center. This change will have no impact on deployments or contributors.
- Releases: The future goal for this project will be for 1 release per year. Django releases Long-Term-Service (LTS) versions approximately every 2 years, so QATrack will attempt to release a matching X.0 release within 6-9 months following the X.2 Django LTS release. This will be followed, about a year later with a feature release (X.1) with additional work that could not be tested in time for the X.0 Release. You should not feel that you have to upgrade to every release, your site will have its own pressures and needs. This project will attempt to support `X.Y -> (X + 3).0` upgrade paths going forward.

With all respect, please grant me as much patience as you can. I welcome all the help you wish to give.

@crcrewso.

## What QATrack+ is

QATrack+ is a tool, used for tracking activities common within equipment maintenance at Radiation Therapy facilities. This, at present, includes QA/QC and Break-Fix/Preventative Maintenance activities. The goal is for this to be a full Quality Management solution for a Radiation Therapy facility.

This is a Free and Open Source (FOSS) project. The goal is to provide a tool for quality management that any site can rely upon, without being tied to a single vendor or deployment solution. This is a Django (web framework) based tool, that needs to be reliable, and approachable.

### Where do I go

- Main deployment and developer documentation can be found on the [Read-The_Docs site](https://docs.qatrackplus.com/en/stable/).
- Community support is available either via [GitHub Discussions](https://github.com/qatrackplus/qatrackplus/discussions) or [Google Groups](https://groups.google.com/g/qatrack)
- FAQ's, community guides for unsupported solutions, rules, and other developer focused information can be found on the [project wiki](https://github.com/qatrackplus/qatrackplus/wiki) currently a work in progress.
- Email - for inquiries not covered within the scope of the above tools, please email [medphys@crcrewso.ca](mailto:medphys@crcrewso.ca)
- Here are the links for the [main website](http://qatrackplus.com) and the [list of users around the world](http://qatrackplus.com/#whos-using). If you would like to be listed, please email us.

### In-Scope

- A limited, well tested number of installation environments
- Upgrade instructions and upgrade paths
- Friendly Documentation
- A place to share community created solutions.

### Out-of-Scope

- Security Model - QATrack+ is designed to be an intranet solution, and should therefore not be directly open to the world wide web.
- Backup - Maintaining day-to-day backups should be handled by best practices of the deployment and the tools available to the site.
- Supporting community solutions - Limited developer resources means that while we will endeavor to support as much as possible, we do not have access to recreate all issues, and thus cannot test

## AI

The world of FOSS has been radically changed by AI in recent years. I'll borrow from the YouTuber [Alberta Tech](https://www.youtube.com/watch?v=PbsocBPkoUc) for some of the language here. Vibe Coding in common use has two distinct meanings, that need to be split out. Agentic AI is where a developer understands a significant portion of what they're trying to accomplish, and relies on tools such as GitHub Copilot, Claude Code, or similar tools. Vibe Coding as originally defined is where someone who only uses prompts, without trying to understand the code at any level. Agentic AI is welcome, it is a collection of tools that many programmers, this maintainer included, have come to rely upon to create time. Unfortunately this project does not have the resources to support code put forward without significant human review. This might change in the future, but for now, please, any contributions need to be understood by the contributor and understandable by the maintainers.

## Funding and Contributions

FOSS projects need backing, and this project is no exception. Up to this point significant sources of project funding have come from The Ottawa Hospital Cancer Centre and the Canadian Nuclear Safety Commission, with a long list of contributors that will be added to this section in short order. Currently the CNSC has provided a grant for helping finalize the localization work, and support Canadian Cancer Centers in upgrading their installations. Over this next year I will be keeping track of nice to have and need to have budgets to keep this project sustainable without relying on a single person. If you would like to support this project, please reach out.

If you would like past contributions to be recognized, please [email](mailto:medphys@crcrewso.ca) We want to acknowledge all contributors, large and small, this includes direct funding, and employer sponsored time.

I would like to specifically call out @randlet for their long history of supporting this project.

<!-- 
### Contributions in kind

This list is unpublished until each member is verified as wanting to be listed, and the list includes a significant % of total contributors

[The Ottawa Hospital Cancer Centre](https://www.ottawahospital.on.ca/en/clinical-services/deptpgrmcs/programs/cancer-program/what-we-offer-our-programs-and-services/radiation-therapy-program/) started this whole project and made sure it was available to an entire international community

[BC Cancer](https://www.bccancer.bc.ca/about/who-we-are) allowing @nsmale contributions to be shared by this community. 

[The Saskatchewan Cancer Agency](https://saskcancer.ca/about-us/who-we-are) funding @ets1199 work implementing localization. 

-->
