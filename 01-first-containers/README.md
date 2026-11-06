# Docker 101 — Your first containers

[Watch tutorial — 21 minutes](https://www.youtube.com/watch?v=g_j--TxlTlI)

From the repository root, run `cd 01-first-containers/docker101` to use the supplied files. Keep this working folder named `docker101`: Compose uses its name for the project and generated image. For the from-scratch walkthrough, use a separate empty folder also named `docker101`, then create `site` inside it. Do not run both copies at once; they share tutorial resource names.

Supplied HTML is the initial page. Later steps change its heading; browser results in those steps assume you made those edits.

Tested in a local Arch development VM. Docker and Neovim must be installed. Use the Docker install page for your distro; Mac users need a running Docker backend such as Docker Desktop. No AWS account needed.

To follow from scratch, create an empty `docker101` folder with a `site` subfolder and open a Bash terminal there. Supplied files are references or a finished starting point; tutorial creates and edits them in Neovim. Read each step and run commands individually. Ports 8080, 8081 and 8090 must be free on the Docker machine. Tutorial names `hello`, `web`, `built-web`, `scratch`, volume `demo-data`, images `mysite:v1`, `mysite:v2` and Compose project `docker101` must be unused.

Adding your account to the Docker group avoids repeated sudo; log out/in after a new assignment. Docker group membership grants root-level control of that machine. Recording packages and image downloads were cached.

Browser addresses refer to the Docker machine. Use a browser inside your VM when following along there. Production browser cutaways reached the same VM through localhost-only SSH forwards; they show real responses.

Expected failures: missing note after replacing a container without a volume; browser cannot connect while web is stopped. Final cleanup deletes only named tutorial data.

## 01 — Welcome and the container basics

### Welcome to Docker 101

### What Docker does

### Image and container

### Containers are not complete virtual machines

## 02 — Get Docker running

### Install packages

```bash
sudo pacman -S --needed docker docker-buildx docker-compose
```

### Start Docker

```bash
sudo systemctl enable --now docker
```

### Use Docker without repeated sudo

```bash
sudo usermod -aG docker "$USER"
```

### Check client and server

```bash
docker version
```

## 03 — Your first container

### Run hello-world

```bash
docker run --name hello hello-world
```

### List running containers

```bash
docker ps
```

### Include stopped containers

```bash
docker ps -a
```

### Remove a finished container

```bash
docker rm hello
```

### Remove a short job automatically

```bash
docker run --rm hello-world
```

## 04 — Run nginx and check it in a browser

### Understand the port mapping

### Start the web server

```bash
docker run -d --name web -p 127.0.0.1:8080:80 nginx:alpine
```

### Read the running container row

```bash
docker ps
```

### Open the nginx welcome page

Open http://127.0.0.1:8080/. Expected: Welcome to nginx!.

### Find the browser request in logs

```bash
docker logs --tail 10 web
```

### Stop the web server

```bash
docker stop web
```

### See what a stopped app looks like

Open http://127.0.0.1:8080/. Expected: connection refused.

### Find the stopped server

```bash
docker ps -a
```

### Start the same container

```bash
docker start web
```

### Verify recovery

Open http://127.0.0.1:8080/. Expected: Welcome to nginx!.

## 05 — Edit your own web page

### Create the page in Neovim

Open `site/index.html` in Neovim.

```
<h1>Hello from varCodeFather</h1>
<p>Docker is serving our page.</p>
```

### Replace the welcome-page container

```bash
docker rm -f web
```

### Mount the site folder

```bash
docker run -d --name web -p 127.0.0.1:8080:80 --mount "type=bind,src=$(pwd)/site,dst=/usr/share/nginx/html,readonly" nginx:alpine
```

### Check your own heading

Open http://127.0.0.1:8080/. Expected: Hello from varCodeFather.

### Change the heading in Neovim

Open `site/index.html` in Neovim.

```
<h1>Updated from my laptop</h1>
```

Replace line 1.

### Refresh without rebuilding

Open http://127.0.0.1:8080/. Expected: Updated from my laptop.

## 06 — Keep data when containers are replaced

### Why a volume exists

### Create a note

Open `note.txt` in Neovim.

```
My Docker note
```

### Create a scratch container

```bash
docker run -d --name scratch alpine:3.24 sleep 3600
```

### Copy and read the note

```bash
docker cp note.txt scratch:/note.txt
docker exec scratch cat /note.txt
```

### Replace the container without storage

```bash
docker rm -f scratch
docker run -d --name scratch alpine:3.24 sleep 3600
```

### Check the missing file

```bash
docker exec scratch cat /note.txt
```

Expected error: `/note.txt` no longer exists in replacement container. Continue to volume example.

### Create the volume

```bash
docker rm -f scratch
docker volume create demo-data
```

### Attach storage at a path

```bash
docker run -d --name scratch --mount type=volume,src=demo-data,dst=/data alpine:3.24 sleep 3600
```

### Put the note in the volume

```bash
docker cp note.txt scratch:/data/note.txt
docker exec scratch cat /data/note.txt
```

### Replace and reattach

```bash
docker rm -f scratch
docker run -d --name scratch --mount type=volume,src=demo-data,dst=/data alpine:3.24 sleep 3600
```

### Verify the note survived

```bash
docker exec scratch cat /data/note.txt
```

## 07 — Build an image with a Dockerfile

### From a live folder to a packaged image

### FROM chooses the starting image

Open `Dockerfile` in Neovim.

```
FROM nginx:alpine
```

### COPY adds our site

Open `Dockerfile` in Neovim.

```
COPY site/ /usr/share/nginx/html/
```

### Save the recipe

Press Escape, type `:wq`, then Enter.

### Build and tag the image

```bash
docker build -t mysite:v1 .
```

### Run the packaged page

```bash
docker run -d --name built-web -p 127.0.0.1:8081:80 mysite:v1
```

### Check both web containers

```bash
docker ps
```

### Open the built copy

Open http://127.0.0.1:8081/. Expected: Updated from my laptop.

### Change only the source

Open `site/index.html` in Neovim.

```
<h1>My packaged Docker page</h1>
```

Replace line 1.

### Compare live files and copied files

Open http://127.0.0.1:8080/. Expected: My packaged Docker page.

Open http://127.0.0.1:8081/. Expected: Updated from my laptop.

### Build the changed page

```bash
docker build -t mysite:v2 .
```

### Replace the old built container

```bash
docker rm -f built-web
docker run -d --name built-web -p 127.0.0.1:8081:80 mysite:v2
```

### Verify the rebuilt page

Open http://127.0.0.1:8081/. Expected: My packaged Docker page.

## 08 — Describe how to run it with Compose

### What Compose does

### Free the original ports

```bash
docker rm -f web built-web
```

### Define a web service

Open `compose.yaml` in Neovim.

```
services:
  web:
```

### Use our Dockerfile for the build

Open `compose.yaml` in Neovim.

```
    build: .
```

### Save the port mapping

Open `compose.yaml` in Neovim.

```
    ports:
      - "127.0.0.1:8080:80"
```

### Save and check the file

Press Escape, type `:wq`, then Enter.

### Validate the configuration

```bash
docker compose config --quiet
```

### Build and start with Compose

```bash
docker compose up -d --build
```

### Check the service status

```bash
docker compose ps
```

### Check the Compose page

Open http://127.0.0.1:8080/. Expected: My packaged Docker page.

### Read this service logs

```bash
docker compose logs --tail 8 web
```

## 09 — Make one change yourself

### Change the published port in Neovim

Open `compose.yaml` in Neovim.

Change `8080` to `8090`.

### Apply the new configuration

```bash
docker compose up -d
```

### Find the new address

```bash
docker compose ps
```

### Verify your change in the browser

Open http://127.0.0.1:8090/. Expected: My packaged Docker page.

## 10 — Clean up and what comes next

### Remove the Compose project containers

```bash
docker compose down
```

### Remove our scratch data deliberately

```bash
docker rm -f scratch
docker volume rm demo-data
```

### Remove our built image tags

```bash
docker image rm mysite:v1 mysite:v2 docker101-web
```

### Check the final container list

```bash
docker ps -a
```

### Where we go next

## References

- [Install Docker](https://docs.docker.com/engine/install/)
- [Docker on Arch](https://wiki.archlinux.org/title/Docker)
- [Docker Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
- [Containers and VMs](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/)
- [Docker group and service](https://docs.docker.com/engine/install/linux-postinstall/)
- [Bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
- [Volumes](https://docs.docker.com/engine/storage/volumes/)
- [Dockerfile](https://docs.docker.com/reference/dockerfile/)
- [Compose](https://docs.docker.com/compose/gettingstarted/)
