package main

import (
    "net/http"
    "net/http/httptest"
    "strings"
    "testing"
)

func TestPageAndHealth(t *testing.T) {
    for _, sample := range []struct{ path string; status int; body string }{
        {"/", http.StatusOK, "Not our greeting"},
        {"/healthz", http.StatusOK, "ok"},
        {"/missing", http.StatusNotFound, "404"},
    } {
        response := httptest.NewRecorder()
        handler(response, httptest.NewRequest(http.MethodGet, sample.path, nil))
        if response.Code != sample.status || !strings.Contains(response.Body.String(), sample.body) {
            t.Fatalf("%s: status=%d body=%q", sample.path, response.Code, response.Body.String())
        }
    }
}
