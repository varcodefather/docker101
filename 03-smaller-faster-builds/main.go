package main

import (
    "html/template"
    "log"
    "net/http"
    "time"

    "github.com/google/uuid"
)

const greeting = "Hello from build one"

var page = template.Must(template.New("page").Parse(`<!doctype html>
<meta charset="utf-8"><title>Docker builds 101</title>
<style>body{background:#101923;color:#edf4f8;font:28px system-ui;max-width:1000px;margin:70px auto}h1{color:#31ceb2}code{font-size:22px}</style>
<h1>{{.Greeting}}</h1><p>Same app. Different Docker build.</p>
<p>Request ID: <code>{{.RequestID}}</code></p>`))

func handler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Cache-Control", "no-store")
    if r.URL.Path == "/healthz" {
        w.Header().Set("Content-Type", "text/plain; charset=utf-8")
        w.Write([]byte("ok"))
        return
    }
    if r.URL.Path != "/" {
        http.NotFound(w, r)
        return
    }
    w.Header().Set("Content-Type", "text/html; charset=utf-8")
    if err := page.Execute(w, struct{ Greeting, RequestID string }{greeting, uuid.NewString()}); err != nil {
        log.Printf("render failed: %v", err)
    }
}

func main() {
    server := &http.Server{Addr: ":8080", Handler: http.HandlerFunc(handler), ReadHeaderTimeout: 5 * time.Second}
    log.Fatal(server.ListenAndServe())
}
