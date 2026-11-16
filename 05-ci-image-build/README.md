# Build and check a container in GitHub Actions

Run tests during the image build, start that image and check its real HTTP
response. No registry login, cloud account or deployment required.

The app is a small Go server. Its Dockerfile runs the tests in a build stage,
then copies the static binary into a non-root runtime image.

## Repository layout

```text
.github/workflows/container-build-101.yml
05-ci-image-build/
  Dockerfile
  main.go
  main_test.go
  go.mod
  go.sum
  smoke_test.py
```

The workflow lives in the repository's root `.github/workflows` folder, not
inside this tutorial folder. Its working directory and path filters refer to
`05-ci-image-build`. Adjust those paths if you move the app into another layout.

## Run locally

From this folder, with Docker running:

```sh
docker build --progress=plain --tag ci-demo:check .
docker run -d --name ci-demo --memory 128m --cpus 0.5 -p 127.0.0.1:18080:8080 ci-demo:check
python3 smoke_test.py http://127.0.0.1:18080
```

Open <http://127.0.0.1:18080>. Expect **Hello from CI** and a request ID.
The smoke script waits briefly for startup, then checks the response content.
It exits unsuccessfully if the app never returns the expected page.

```sh
docker logs ci-demo
docker rm -f ci-demo
docker image rm ci-demo:check
```

## Follow a real Actions run

Read [the workflow](../.github/workflows/container-build-101.yml). It uses:

- A standard GitHub-hosted Ubuntu runner and a ten-minute job timeout.
- Read-only repository contents permission, with checkout credentials not retained.
- The commit that triggered the push or pull request.
- A Docker build containing the Go tests, followed by the real app smoke check.
- An always-run cleanup step that shows container logs if a container exists.

Push this folder and the workflow to `main`, open a pull request affecting these
files, or use the workflow's **Run workflow** button. Open **Actions → Container
build 101**, select the run and read the build and smoke-check steps. Check the
run's commit matches your change before trusting its result.

## Reproduce a useful failure

On a separate tutorial branch, edit the home-page sample in `main_test.go`:

```go
{"/", http.StatusOK, "Not our greeting"},
```

The app still serves its normal greeting, so this deliberately wrong assertion
makes the test fail. Commit and push through a pull request, then inspect the
actual failed build step. The smoke step should be skipped because the image
build did not succeed. Correct the expectation back to `greeting`, commit again
and inspect the new run for that repaired commit.

A successful build here does not publish an image or deploy anything. The image
exists only on that temporary runner. This workflow uploads no image archive,
Actions cache or build artifact, and requests no package-write permission.

## References

- [Checkout action](https://github.com/actions/checkout)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
