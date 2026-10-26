# Your own Python packages

Calculation procedures can use Python packages that QATrack+ does not install
itself, such as pint. List them, one per line, in a file named
`requirements.txt` in this folder, then rebuild the image:

```
pint==0.24.4
```

```bash
docker compose build
docker compose up -d
```

- Pin each package you list (`==`). Packages they depend on that QATrack+
  doesn't already include are picked when the image is built, so a later
  rebuild can get newer ones; pin those too if every rebuild must be identical.
- Docker only reinstalls these packages when something in this folder, or
  QATrack+'s own dependencies, change. To force it, run
  `docker compose build --no-cache django`.
- QATrack+ already includes numpy, scipy, pandas, matplotlib, pydicom, pylinac
  and others; you don't need to list them. The versions it uses are in `uv.lock`
  at the top of your QATrack+ folder.
- Packages are installed only at versions that work with QATrack+'s own
  dependencies. If one needs a different version of something QATrack+ uses
  (Django, numpy, pylinac, ...), the build stops and says which, rather than
  changing what QATrack+ runs on.
- On a server without internet access, put wheel files for the packages and
  everything they depend on in this folder, and add a line `--no-index` at the
  top of `requirements.txt`. The wheels must suit the image: Linux, CPython 3.12
  and the server's processor (use `aarch64` in place of `x86_64` on ARM). On any
  computer with internet access, this fetches them into `site-wheels`:

  ```
  pip download --only-binary=:all: --python-version 3.12 --implementation cp --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 -d site-wheels pint==0.24.4
  ```

  The rest of the build still needs the internet unless the image was built
  once on this server while it was online, or you build it elsewhere and move
  it with `docker save` and `docker load`.
- Packages that need system libraries the image does not have may fail to build,
  or fail when imported.

`requirements.txt` and any wheel files here are yours: git ignores them, so
`git pull` never changes them. See "Adding Python packages" in the Docker
installation guide for more.
