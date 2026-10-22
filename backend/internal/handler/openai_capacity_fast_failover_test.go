package handler

import (
	"context"
	"net/http"
	"testing"
	"time"

	"github.com/Wei-Shaw/sub2api/internal/service"
	"github.com/stretchr/testify/require"
)

func TestOpenAICapacitySkipsSameAccountRetry(t *testing.T) {
	for _, payload := range []string{
		`{"error":{"code":"server_is_overloaded","message":"overloaded"}}`,
		`{"type":"response.failed","response":{"error":{"code":"slow_down"}}}`,
		`{"error":{"message":"Our servers are currently overloaded. Please try again later."}}`,
	} {
		t.Run(payload, func(t *testing.T) {
			err := &service.UpstreamFailoverError{
				StatusCode:               http.StatusServiceUnavailable,
				ResponseBody:             []byte(payload),
				RetryableOnSameAccount:   true,
				RequestScopedTransient:   true,
				SameAccountRetryDeadline: time.Now().Add(time.Minute),
			}
			require.True(t, err.IsOpenAICapacityShed())
			// A high configured count or an OAuth retry window must not turn an
			// explicit overload into repeated attempts on the same account.
			require.False(t, sameAccountRetryAllowed(err, 0, 10))
			require.False(t, sameAccountRetryAllowed(err, 0, 0))
		})
	}
}

func TestOpenAICapacityFastFailoverPreservesOtherRetries(t *testing.T) {
	for _, tc := range []struct {
		name    string
		payload string
		status  int
	}{
		{"ordinary OAuth 429", `{"error":{"code":"rate_limit_exceeded","message":"Rate limit exceeded"}}`, http.StatusTooManyRequests},
		{"generic transient", `{"error":{"code":"server_error","message":"temporary failure"}}`, http.StatusBadGateway},
		{"overload mentioned only in echoed input", `{"error":{"code":"invalid_request_error","message":"Invalid schema"},"input":"server_is_overloaded"}`, http.StatusBadRequest},
	} {
		t.Run(tc.name, func(t *testing.T) {
			err := &service.UpstreamFailoverError{
				StatusCode:             tc.status,
				ResponseBody:           []byte(tc.payload),
				RetryableOnSameAccount: true,
				RequestScopedTransient: true,
			}
			require.False(t, err.IsOpenAICapacityShed())
			require.True(t, sameAccountRetryAllowed(err, 0, maxSameAccountRetries))
			err.SameAccountRetryDeadline = time.Now().Add(time.Minute)
			require.True(t, sameAccountRetryAllowed(err, 100, 0))
		})
	}
}

func TestOpenAICapacitySwitchesOnFirstFailureWithinExistingBudget(t *testing.T) {
	fs := NewFailoverState(1, false)
	unscheduler := &mockTempUnscheduler{}
	err := &service.UpstreamFailoverError{
		StatusCode:             http.StatusServiceUnavailable,
		ResponseBody:           []byte(`{"error":{"code":"server_is_overloaded"}}`),
		RetryableOnSameAccount: true,
		RequestScopedTransient: true,
	}

	action := fs.HandleFailoverError(context.Background(), unscheduler, 17, service.PlatformOpenAI, maxSameAccountRetries, err)
	require.Equal(t, FailoverContinue, action)
	require.Equal(t, 1, fs.SwitchCount)
	require.Contains(t, fs.FailedAccountIDs, int64(17))
	require.Empty(t, fs.SameAccountRetryCount)
	require.True(t, err.RequestScopedTransient, "capacity must retain the no-account-ban classification")

	action = fs.HandleFailoverError(context.Background(), unscheduler, 25, service.PlatformOpenAI, maxSameAccountRetries, err)
	require.Equal(t, FailoverExhausted, action)
	require.Equal(t, 1, fs.SwitchCount)
	require.Contains(t, fs.FailedAccountIDs, int64(25))
	require.Empty(t, fs.SameAccountRetryCount)
}
