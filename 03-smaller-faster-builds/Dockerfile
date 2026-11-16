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
