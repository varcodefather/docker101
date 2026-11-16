# Smaller images and better build caching

Build the same Go web app three ways. Keep unrelated files out of its context,
separate dependency inputs from source changes, then copy a tested binary into
a small runtime image. Go runs inside the build container; no host Go install needed.

Requirements: working Docker with BuildKit, browser, text editor. Linux shown;
macOS/Windows need their Docker backend running. Commands below use a Linux shell.

## Start clean

From this repository folder, copy the starter into a new local directory:

```sh
mkdir -p ~/tutorials
cp -R starter ~/tutorials/docker-builds
cd ~/tutorials/docker-builds
```

Use a new destination; don't mix this exercise with a folder containing your data.
The completed Dockerfiles are above `starter` for reference.

## Isolate this comparison

An earlier run can leave future source versions in a builder's cache. Use a new,
disposable builder for this exercise so each cache comparison starts from a known
history. Default load makes its results available to local `docker run`; memory
and CPU options cap the lab builder. Existing shared caches remain untouched.

```sh
docker buildx create --name builds101 --driver docker-container --driver-opt default-load=true,memory=1536m,memory-swap=1536m,cpu-period=100000,cpu-quota=200000
export BUILDX_BUILDER=builds101
docker buildx inspect --bootstrap
```

Use an unused builder name. Keep the export in this terminal for every build below.

## Baseline

```sh
dd if=/dev/urandom of=debug.dump bs=1M count=8
ls -lh debug.dump
docker build --progress=plain -f Dockerfile.naive -t builds101:naive .
docker run -d --name builds101-naive --memory 128m --cpus 0.5 -p 127.0.0.1:18084:8080 builds101:naive
docker ps --filter name=builds101-naive
docker run --rm --entrypoint sh builds101:naive -c "ls -lh /src/debug.dump"
```

Open <http://127.0.0.1:18084>. Expect **Hello from build one** and a request ID.
Reload changes that ID. The dump is random demo data; never use a real backup here.

Open `main.go` in your editor and change `Hello from build one` to
`Hello from build two`. Save, then rebuild:

```sh
docker build --progress=plain -f Dockerfile.naive -t builds101:naive-rebuild .
```

The broad `COPY . .` precedes `go mod download`, so a source edit invalidates that
dependency instruction too. Existing containers still run their original images.

## Exclude local files

Create `.dockerignore` with:

```text
.git
*.log
*.dump
Dockerfile*
README.md
dockerignore.example
```

```sh
docker build --progress=plain -f Dockerfile.naive -t builds101:ignored .
docker run --rm --entrypoint sh builds101:ignored -c "ls -lh /src"
dd if=/dev/zero of=debug.dump bs=1M count=1
docker build --progress=plain -f Dockerfile.naive -t builds101:ignored-rebuild .
```

The dump is absent from `/src`. Changing only that ignored file preserves the
app's cached build instruction. Ignore rules exclude context inputs; they don't
remove secrets from old images or protect files obtained by later build commands.

## Separate dependency and source inputs

Create `Dockerfile.cached`:

```dockerfile
FROM golang:1.27.4-alpine
ENV GOMAXPROCS=2
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go test ./... && CGO_ENABLED=0 go build -o /server .
USER 1000:1000
EXPOSE 8080
CMD ["/server"]
```

```sh
docker build --progress=plain -f Dockerfile.cached -t builds101:cached .
```

Edit the greeting from `build two` to `build three`, save, then:

```sh
docker build --progress=plain -f Dockerfile.cached -t builds101:cached-rebuild .
docker image ls --filter reference="builds101:*"
```

`go mod download` should be cached while the source copy and test/build instruction
run again. This image still contains the compiler base; instruction ordering by
itself doesn't remove build tools or guarantee a large elapsed-time improvement.

## Build stage and runtime stage

Create `Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.27.4-alpine AS build
ENV GOMAXPROCS=2
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build \
    go test ./... && CGO_ENABLED=0 go build -o /server .

FROM scratch
COPY --from=build /server /server
USER 1000:1000
EXPOSE 8080
CMD ["/server"]
```

```sh
docker build --progress=plain -f Dockerfile -t builds101:runtime .
docker image inspect builds101:naive builds101:runtime --format "{{.RepoTags}} bytes={{.Size}} user={{.Config.User}}"
docker run -d --name builds101-runtime --memory 128m --cpus 0.5 -p 127.0.0.1:18085:8080 builds101:runtime
docker ps --filter name=builds101-runtime
```

Open <http://127.0.0.1:18085>. Expect **Hello from build three**. The static binary
serves the same app without the compiler image underneath it. These commands
intentionally fail because the runtime has neither shell nor Go compiler:

```sh
docker exec builds101-runtime /bin/sh -c true
docker exec builds101-runtime /usr/local/go/bin/go version
```

`scratch` fits this HTTP-only static demo. Other apps may need a runtime,
shared libraries, certificates or timezone files; include what your app uses.
Cache mounts persist build-tool caches in the builder, not in the final runtime.

## Incremental edit

Change the greeting from `build three` to `build four`, save, then:

```sh
docker build --progress=plain -f Dockerfile -t builds101:runtime-rebuild .
docker rm -f builds101-runtime
docker run -d --name builds101-runtime --memory 128m --cpus 0.5 -p 127.0.0.1:18085:8080 builds101:runtime-rebuild
docker ps --filter name=builds101-runtime
```

Reload <http://127.0.0.1:18085> and check **Hello from build four**. Source edits
rerun the app instruction while Go can reuse suitable module/compiler cache work.

## What the measurements mean

The real local rehearsal measured approximately 562 million Docker-reported local image bytes
for the naive image and 21 million for this runtime. Your builds may differ.
The containerd store keeps compressed and unpacked image data. This reported size
isn't registry transfer or additional disk space
used by one tag; layers and caches can be shared. Read actual cache steps instead
of treating these local timings as a benchmark for another machine or project.

## A failed test must block the image

Open `main_test.go`. Replace the home-page sample's expected value `greeting`
with `"Not our greeting"`, then save. This deliberately wrong assertion should
fail while the app still serves its real greeting.

```sh
docker build --progress=plain -f Dockerfile -t builds101:rejected .
docker image inspect builds101:rejected
docker ps --filter name=builds101-runtime
```

Expect `TestPageAndHealth` to fail, the build to stop and the rejected tag to be
absent. The previously running container remains available. Restore the expected
value to `greeting` and save, then:

```sh
docker build --progress=plain -f Dockerfile -t builds101:runtime-verified .
docker rm -f builds101-runtime
docker run -d --name builds101-runtime --memory 128m --cpus 0.5 -p 127.0.0.1:18085:8080 builds101:runtime-verified
docker ps --filter name=builds101-runtime
```

Restoring identical previously successful inputs can reuse the successful cache
entry; the failed test wasn't cached as a success. Reload port 18085 and check
**Hello from build four** from the verified image.

## Cleanup

```sh
docker rm -f builds101-naive builds101-runtime
docker image rm builds101:naive builds101:naive-rebuild builds101:ignored builds101:ignored-rebuild builds101:cached builds101:cached-rebuild builds101:runtime builds101:runtime-rebuild builds101:runtime-verified
unset BUILDX_BUILDER
docker buildx rm builds101
```

Source files remain. Only the disposable builder and its cache are removed; shared caches remain.

## References

- [Docker build cache](https://docs.docker.com/build/cache/optimize/)
- [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Official Go image](https://hub.docker.com/_/golang)
