# Find and repair common Docker faults

Run a small counter, save data, then diagnose four deliberate faults:
missing environment setting, busy host port, read-only mount and wrong directory
owner. Check container state, logs and effective configuration before repairing
each fault. Keep the saved value throughout.

This exact ownership exercise uses rootful Docker on Linux and a local user with
UID 1000, matching the image's non-root user. Docker Desktop and rootless engines
can map host file ownership differently. Use a Linux VM for this exact sequence.

## Working reference

Copy this folder into `~/tutorials/docker-debugging` and work there:

```sh
cd ~/tutorials/docker-debugging
cp .env.example .env
mkdir data
id -u
ls -ld data
docker build -t debug-counter:v1 .
docker run -d --name debug101-app --memory 128m --cpus 0.5 --env-file .env --mount type=bind,src="$PWD/data",dst=/data -p 127.0.0.1:18086:8000 debug-counter:v1
docker ps --filter name=debug101-app
```

Use a fresh directory for the exercise. `id -u` should be 1000 for these files.
Open <http://127.0.0.1:18086>, click **Add one** twice, then open
`data/counter.json` in your editor. Browser and file should both show **2**.

## Missing setting: process exits

Read `missing-setting.env`: it omits the required `GREETING` value.

```sh
docker run -d --name debug101-missing --memory 128m --cpus 0.5 --env-file missing-setting.env -p 127.0.0.1:18087:8000 debug-counter:v1
docker ps -a --filter name=debug101-missing
docker logs debug101-missing
docker inspect debug101-missing --format "status={{.State.Status}} exit={{.State.ExitCode}}"
```

Expect an exited process, nonzero exit code and a `KeyError` naming `GREETING`.
The container ID returned by `run -d` did not guarantee the app would stay up.

```sh
docker rm debug101-missing
docker run -d --name debug101-missing --memory 128m --cpus 0.5 --env-file .env -p 127.0.0.1:18087:8000 debug-counter:v1
```

Open <http://127.0.0.1:18087>. This separate container should show the greeting
and count **0**: it doesn't mount the original app's host data directory.
Changing an environment file doesn't update an existing container's environment;
the replacement supplies the corrected setting.

```sh
docker rm -f debug101-missing
```

## Busy host port: Docker rejects publication

The original container still owns localhost port 18086:

```sh
docker run -d --name debug101-busy --memory 128m --cpus 0.5 --env-file .env -p 127.0.0.1:18086:8000 debug-counter:v1
docker ps -a --filter name=debug101-
docker port debug101-app 8000
```

Expect the publish error to name an allocated/busy port. In the tested Docker
version the failed example remains in `created` state. The original app still
answers on 18086 with saved count **2**.

```sh
docker rm debug101-busy
docker run -d --name debug101-busy --memory 128m --cpus 0.5 --env-file .env -p 127.0.0.1:18087:8000 debug-counter:v1
```

Open <http://127.0.0.1:18087>. Only the host side of the mapping changed; the app
still listens on container port 8000. Remove this spare before continuing:

```sh
docker rm -f debug101-busy
```

## Read-only mount: reads work, saves fail

Replace the original app while retaining its host data folder:

```sh
docker rm -f debug101-app
docker run -d --name debug101-app --memory 128m --cpus 0.5 --env-file .env --mount type=bind,src="$PWD/data",dst=/data,readonly -p 127.0.0.1:18086:8000 debug-counter:v1
```

Reload 18086. It should read **2**. Click **Add one**: expect a save failure
containing **Read-only file system**, with the value still **2**.

```sh
docker ps --filter name=debug101-app
docker logs --tail 20 debug101-app
docker inspect debug101-app --format "{{range .Mounts}}{{.Source}} -> {{.Destination}} writable={{.RW}}{{println}}{{end}}"
```

The app process is still running. Its effective `/data` mount has `writable=false`.
Read `data/counter.json` again before repairing; it still contains **2**.

```sh
docker rm -f debug101-app
docker run -d --name debug101-app --memory 128m --cpus 0.5 --env-file .env --mount type=bind,src="$PWD/data",dst=/data -p 127.0.0.1:18086:8000 debug-counter:v1
```

Reload, check **2**, then add one and check **3** in browser and host file.
A restart of the read-only container would retain its original mount settings.

## Writable mount, wrong directory owner

Use a small helper container to change only this disposable directory's owner:

```sh
docker run --rm --user 0:0 --mount type=bind,src="$PWD/data",dst=/data --entrypoint chown debug-counter:v1 0:0 /data
```

Reload the app to read **3**, then try saving. Expect **Permission denied**.
The directory still permits reading, but app UID 1000 cannot create a temporary
file in a root-owned directory with its normal permissions.

```sh
docker exec debug101-app id
docker exec debug101-app ls -ldn /data
docker inspect debug101-app --format "{{range .Mounts}}{{.Destination}} writable={{.RW}}{{println}}{{end}}"
```

Compare process UID 1000, directory owner 0 and `writable=true`. This differs from
the previous read-only-mount fault even though both prevented a save.

```sh
docker run --rm --user 0:0 --mount type=bind,src="$PWD/data",dst=/data --entrypoint chown debug-counter:v1 1000:1000 /data
```

No app restart required. Reload, add one and check **4** in browser and host file.
The directory now has its original owner again.

## Edited environment file, stale container setting

Edit `.env`, changing `GREETING=Hello from Docker` to
`GREETING=Hello from updated settings`, and save. Reload port 18086: the existing
container should still show the original greeting with count **4**.

```sh
docker restart debug101-app
docker exec debug101-app printenv GREETING
```

The restart still uses `Hello from Docker`. Docker doesn't reread `--env-file`
as new creation settings when restarting an existing container. Recreate it:

```sh
docker rm -f debug101-app
docker run -d --name debug101-app --memory 128m --cpus 0.5 --env-file .env --mount type=bind,src="$PWD/data",dst=/data -p 127.0.0.1:18086:8000 debug-counter:v1
```

Reload. Expect **Hello from updated settings** and count **4**. Add one and check
**5**, including in the host file. Image and saved data were retained while the
replacement received the new runtime environment.

## Cleanup

```sh
docker rm -f debug101-app
docker image rm debug-counter:v1
```

The host data directory and source files remain. No global prune or volume
deletion needed. All credentials/settings in these files are disposable examples.

## References

- [Run containers](https://docs.docker.com/engine/containers/run/)
- [Bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
- [Inspect a container](https://docs.docker.com/reference/cli/docker/container/inspect/)
