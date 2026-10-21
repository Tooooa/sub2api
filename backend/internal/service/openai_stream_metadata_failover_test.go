package service

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/Wei-Shaw/sub2api/internal/config"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
)

func TestOpenAIResponseMetadataDoesNotStartOutput(t *testing.T) {
	data := `{"type":"response.metadata","sequence_number":2,"metadata":{"request_id":"attempt-metadata"}}`
	require.False(t, openAIStreamDataStartsClientOutput(data, "response.metadata"))
	require.False(t, openAIStreamDataStartsVisibleOutput(data, "response.metadata"))
	require.False(t, openAIStreamDataStartsSemanticTTFT(data, "response.metadata"))
	// Preserve the conservative behavior for unrecognized events.
	require.True(t, openAIStreamDataStartsClientOutput(`{"type":"unknown_event"}`, "unknown_event"))
}

// Production emitted created -> in_progress -> metadata -> error -> failed,
// with empty output. Neither attempt metadata nor its error may reach a client
// when a subsequent account can complete the same request.
func TestOpenAIStreamMetadataOverloadCanRetryAnotherAccount(t *testing.T) {
	gin.SetMode(gin.TestMode)
	for _, passthrough := range []bool{false, true} {
		name := map[bool]string{false: "native", true: "passthrough"}[passthrough]
		t.Run(name, func(t *testing.T) {
			svc := &OpenAIGatewayService{cfg: &config.Config{Gateway: config.GatewayConfig{MaxLineSize: defaultMaxLineSize}}}
			rec := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(rec)
			c.Request = httptest.NewRequest(http.MethodPost, "/v1/responses", nil)
			failed := strings.Join([]string{
				`data: {"type":"response.created","response":{"id":"resp_failed_attempt","metadata":{"padding":"` + strings.Repeat("x", 64*1024) + `"}}}`,
				"",
				`data: {"type":"response.in_progress","response":{"id":"resp_failed_attempt","output":[]}}`,
				"",
				"event: response.metadata",
				`data: {"type":"response.metadata","metadata":{"request_id":"failed-attempt-metadata"}}`,
				"",
				"event: error",
				`data: {"type":"error","error":{"code":"server_is_overloaded","message":"Our servers are currently overloaded. Please try again later."}}`,
				"",
				"event: response.failed",
				`data: {"type":"response.failed","response":{"id":"resp_failed_attempt","output":[],"error":{"code":"server_is_overloaded","message":"Our servers are currently overloaded. Please try again later."}}}`,
				"", "",
			}, "\n")
			succeeded := strings.Join([]string{
				`data: {"type":"response.created","response":{"id":"resp_success"}}`, "",
				`data: {"type":"response.metadata","metadata":{"request_id":"successful-attempt-metadata"}}`, "",
				`data: {"type":"response.output_text.delta","delta":"recovered output"}`, "",
				`data: {"type":"response.completed","response":{"id":"resp_success","status":"completed","usage":{"input_tokens":3,"output_tokens":2}}}`, "", "",
			}, "\n")
			for attempt, body := range []string{failed, succeeded} {
				account := &Account{ID: int64(attempt + 1), Platform: PlatformOpenAI, Type: AccountTypeOAuth}
				resp := &http.Response{StatusCode: http.StatusOK, Header: make(http.Header), Body: io.NopCloser(strings.NewReader(body))}
				var err error
				if passthrough {
					_, err = svc.handleStreamingResponsePassthrough(c.Request.Context(), resp, c, account, time.Now(), "model", "model")
				} else {
					_, err = svc.handleStreamingResponse(c.Request.Context(), resp, c, account, time.Now(), "model", "model")
				}
				if attempt == 0 {
					var failoverErr *UpstreamFailoverError
					require.ErrorAs(t, err, &failoverErr)
					require.True(t, failoverErr.RequestScopedTransient)
					require.False(t, c.Writer.Written())
					require.Empty(t, rec.Body.String())
				} else {
					require.NoError(t, err)
				}
			}
			body := rec.Body.String()
			require.Contains(t, body, "recovered output")
			require.Contains(t, body, "successful-attempt-metadata")
			require.NotContains(t, body, "failed-attempt-metadata")
			require.NotContains(t, body, "resp_failed_attempt")
			require.NotContains(t, body, "overloaded")
			require.NotContains(t, body, "response.failed")
			require.Equal(t, 1, strings.Count(body, "response.completed"))
		})
	}
}

func TestOpenAIStreamMetadataDoesNotAllowReplayAfterRealOutput(t *testing.T) {
	gin.SetMode(gin.TestMode)
	for _, passthrough := range []bool{false, true} {
		for _, output := range []string{
			`{"type":"response.output_text.delta","delta":"partial output"}`,
			`{"type":"response.function_call_arguments.delta","delta":"{\"path\":"}`,
		} {
			name := map[bool]string{false: "native", true: "passthrough"}[passthrough] + "/" + output
			t.Run(name, func(t *testing.T) {
				svc := &OpenAIGatewayService{cfg: &config.Config{Gateway: config.GatewayConfig{MaxLineSize: defaultMaxLineSize}}}
				rec := httptest.NewRecorder()
				c, _ := gin.CreateTestContext(rec)
				c.Request = httptest.NewRequest(http.MethodPost, "/v1/responses", nil)
				body := "data: {\"type\":\"response.metadata\"}\n\n" +
					"data: " + output + "\n\n" +
					"data: {\"type\":\"response.failed\",\"response\":{\"error\":{\"code\":\"server_is_overloaded\",\"message\":\"Our servers are currently overloaded. Please try again later.\"}}}\n\n"
				resp := &http.Response{StatusCode: http.StatusOK, Header: make(http.Header), Body: io.NopCloser(strings.NewReader(body))}
				account := &Account{ID: 1, Platform: PlatformOpenAI, Type: AccountTypeOAuth}
				var err error
				if passthrough {
					_, err = svc.handleStreamingResponsePassthrough(c.Request.Context(), resp, c, account, time.Now(), "model", "model")
				} else {
					_, err = svc.handleStreamingResponse(c.Request.Context(), resp, c, account, time.Now(), "model", "model")
				}
				require.Error(t, err)
				var failoverErr *UpstreamFailoverError
				require.False(t, errors.As(err, &failoverErr))
				require.True(t, c.Writer.Written())
				require.Equal(t, 1, strings.Count(rec.Body.String(), "response.failed"))
			})
		}
	}
}

func TestOpenAIWSHTTPBridgeMetadataOverloadCanFailOver(t *testing.T) {
	gin.SetMode(gin.TestMode)
	body := "data: {\"type\":\"response.created\",\"response\":{\"id\":\"resp_failed_attempt\"}}\n\n" +
		"data: {\"type\":\"response.metadata\",\"metadata\":{\"request_id\":\"failed-attempt-metadata\"}}\n\n" +
		"data: {\"type\":\"error\",\"error\":{\"code\":\"server_is_overloaded\",\"message\":\"Our servers are currently overloaded. Please try again later.\"}}\n\n"
	upstream := &httpUpstreamRecorder{resp: &http.Response{StatusCode: http.StatusOK, Header: make(http.Header), Body: io.NopCloser(strings.NewReader(body))}}
	svc := &OpenAIGatewayService{cfg: &config.Config{}, httpUpstream: upstream}
	account := &Account{ID: 1, Platform: PlatformOpenAI, Type: AccountTypeOAuth, Concurrency: 1}
	rec := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(rec)
	c.Request = httptest.NewRequest(http.MethodGet, "/v1/responses", nil)
	payload := []byte(`{"type":"response.create","model":"gpt-5","input":"hi"}`)
	var writes [][]byte
	_, err := svc.proxyOpenAIWSHTTPBridgeTurn(context.Background(), c, account, "sk-test", payload, len(payload),
		"gpt-5", "", "", "", "", 1, func(message []byte) error {
			writes = append(writes, append([]byte(nil), message...))
			return nil
		})
	var failoverErr *UpstreamFailoverError
	require.ErrorAs(t, err, &failoverErr)
	require.True(t, failoverErr.RequestScopedTransient)
	require.Empty(t, writes)
}
