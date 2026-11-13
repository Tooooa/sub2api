//go:build unit

package service

import (
	"context"
	"fmt"
	"net/http"
	"testing"
	"time"

	"github.com/Wei-Shaw/sub2api/internal/config"
	"github.com/stretchr/testify/require"
)

type capabilityQuotaRepo struct {
	oauth429RateLimitRepo
	account *Account
}

func (r *capabilityQuotaRepo) SetModelRateLimit(ctx context.Context, id int64, scope string, until time.Time, reason ...string) error {
	_ = r.oauth429RateLimitRepo.SetModelRateLimit(ctx, id, scope, until, reason...)
	if r.account.Extra == nil {
		r.account.Extra = map[string]any{}
	}
	limits, _ := r.account.Extra[modelRateLimitsKey].(map[string]any)
	if limits == nil {
		limits = map[string]any{}
		r.account.Extra[modelRateLimitsKey] = limits
	}
	limits[scope] = map[string]any{"rate_limit_reset_at": until.UTC().Format(time.RFC3339)}
	return nil
}

func nativeImagesQuotaContext() context.Context {
	return WithOpenAIImagesEndpoint(WithOpenAIImageGenerationIntent(context.Background()))
}

func TestCodexQuotaCapabilityIsolation(t *testing.T) {
	for _, native := range []bool{false, true} {
		t.Run(fmt.Sprintf("native_images=%v", native), func(t *testing.T) {
			account := &Account{ID: 44, Platform: PlatformOpenAI, Type: AccountTypeOAuth, Status: StatusActive, Schedulable: true}
			repo := &capabilityQuotaRepo{account: account}
			limits := NewRateLimitService(repo, nil, &config.Config{}, nil, nil)
			gateway := &OpenAIGatewayService{rateLimitService: limits}
			limits.SetAccountRuntimeBlocker(gateway)
			ctx, model := context.Background(), "gpt-6-astra"
			wantScope := openAICodexTextQuotaKey
			if native {
				ctx, model, wantScope = nativeImagesQuotaContext(), "gpt-image-2.5-flare", openAIImageGenerationRateLimitKey
			}
			// Actual production error shape: a text weekly quota must not take
			// the account out of the native Images pool for the whole week.
			resetAt := time.Now().Add(6 * 24 * time.Hour)
			body := []byte(fmt.Sprintf(`{"error":{"type":"usage_limit_reached","message":"The usage limit has been reached","limit_window_minutes":10080,"resets_at":%d,"resets_in_seconds":518400}}`, resetAt.Unix()))
			require.False(t, gateway.handleOpenAIAccountUpstreamError(ctx, account, http.StatusTooManyRequests, nil, body, model))
			require.Zero(t, repo.setRateLimitedCalls, "capability quota must not persist an account-wide cooldown")
			require.False(t, gateway.isOpenAIAccountRuntimeBlocked(account))
			require.Equal(t, wantScope, repo.lastModelRateLimitKey)
			require.WithinDuration(t, resetAt, repo.lastModelRateLimitedUntil, time.Second)
			require.Equal(t, !native, account.isModelRateLimitedWithContext(context.Background(), "gpt-6.1-sol"))
			require.Equal(t, native, account.isModelRateLimitedWithContext(nativeImagesQuotaContext(), "gpt-image-2.5-flare"))
			if !native {
				require.True(t, account.isModelRateLimitedWithContext(WithOpenAIImageGenerationIntent(context.Background()), "gpt-6.1-sol"), "Responses image tools still consume the text driver")
				require.False(t, account.isModelRateLimitedWithContext(context.Background(), "gpt-5.3-codex-spark"))
			}
			// Expiration itself restores eligibility; no admin query is needed.
			require.NoError(t, repo.SetModelRateLimit(ctx, account.ID, wantScope, time.Now().Add(-time.Second)))
			require.False(t, account.isModelRateLimitedWithContext(ctx, model))
		})
	}
}

func TestNativeImagesDoNotInheritTextQuotaAutoPause(t *testing.T) {
	account := &Account{ID: 44, Platform: PlatformOpenAI, Type: AccountTypeOAuth, Extra: map[string]any{
		"auto_pause_7d_threshold": 0.95,
		"codex_7d_used_percent":   100.0,
		"codex_7d_reset_at":       time.Now().Add(6 * 24 * time.Hour).Format(time.RFC3339),
		"codex_usage_updated_at":  time.Now().Format(time.RFC3339),
	}}
	for _, tc := range []struct {
		name   string
		ctx    context.Context
		model  string
		paused bool
	}{
		{"text", context.Background(), "gpt-6.1-sol", true},
		{"native", nativeImagesQuotaContext(), "gpt-image-2.5-flare", false},
		{"responses_tool", WithOpenAIImageGenerationIntent(context.Background()), "gpt-6.1-sol", true},
		{"responses_image_alias", WithOpenAIImageGenerationIntent(context.Background()), "gpt-image-2.5-flare", true},
		{"legacy_image_bridge", nativeImagesQuotaContext(), "gpt-image-1", true},
		{"forced_responses", withOpenAIImagesForceResponses(nativeImagesQuotaContext()), "gpt-image-2.5-flare", true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			paused, _ := shouldAutoPauseOpenAIAccountByQuota(tc.ctx, account, tc.model)
			require.Equal(t, tc.paused, paused)
		})
	}
	account.Credentials = map[string]any{"model_mapping": map[string]any{"public-image": "gpt-image-2.5-flare"}}
	paused, _ := shouldAutoPauseOpenAIAccountByQuota(nativeImagesQuotaContext(), account, "public-image")
	require.False(t, paused, "native eligibility follows the mapped upstream model")
}

func TestNativeImagesQuotaIsolationPreservesAccountRestrictions(t *testing.T) {
	account := &Account{ID: 44, Platform: PlatformOpenAI, Type: AccountTypeOAuth, Status: StatusActive, Schedulable: true}
	eligible := func() bool {
		return isOpenAICompatibleAccountEligibleForRequest(nativeImagesQuotaContext(), account, PlatformOpenAI, "gpt-image-2.5-flare", false, OpenAIEndpointCapabilityResponses)
	}
	account.Extra = map[string]any{modelRateLimitsKey: map[string]any{
		openAICodexTextQuotaKey: map[string]any{"rate_limit_reset_at": time.Now().Add(time.Hour).Format(time.RFC3339)},
	}}
	require.True(t, eligible(), "text quota alone cannot remove the account from the native image pool")
	account.Status = StatusError
	require.False(t, eligible(), "invalid/disabled credentials stay blocked")
	account.Status = StatusActive
	account.Schedulable = false
	require.False(t, eligible(), "operator disable stays blocked")
	account.Schedulable = true
	until := time.Now().Add(time.Hour)
	account.TempUnschedulableUntil = &until
	require.False(t, eligible(), "authentication or risk cooldown stays blocked")
	account.TempUnschedulableUntil = nil
	account.Extra[modelRateLimitsKey].(map[string]any)[openAIImageGenerationRateLimitKey] = map[string]any{"rate_limit_reset_at": until.Format(time.RFC3339)}
	require.False(t, eligible(), "image quota remains enforced")
}

type capabilityQuotaProbeRepo struct {
	stubQuotaAccountRepo
	modelScopes []string
}

func (r *capabilityQuotaProbeRepo) SetModelRateLimit(_ context.Context, _ int64, scope string, _ time.Time, _ ...string) error {
	r.modelScopes = append(r.modelScopes, scope)
	return nil
}

func TestTextQuotaRecoveryPreservesOtherModelRestrictions(t *testing.T) {
	account := &Account{ID: 44, Platform: PlatformOpenAI, Type: AccountTypeOAuth, Extra: map[string]any{
		modelRateLimitsKey: map[string]any{},
	}}
	entries := account.Extra[modelRateLimitsKey].(map[string]any)
	for _, key := range []string{openAICodexTextQuotaKey, openAIImageGenerationRateLimitKey, "gpt-5.3-codex-spark", "gpt-plan-restricted"} {
		entries[key] = map[string]any{"rate_limit_reset_at": time.Now().Add(time.Hour).Format(time.RFC3339)}
	}
	repo := &capabilityQuotaProbeRepo{stubQuotaAccountRepo: stubQuotaAccountRepo{accounts: map[int64]*Account{44: account}}}
	svc := &OpenAIQuotaService{accountRepo: repo}
	svc.clearQuotaRuntimeStateBestEffort(context.Background(), 44, "quota_query", false)
	require.Equal(t, []string{openAICodexTextQuotaKey}, repo.modelScopes)
	require.Empty(t, repo.clearModelRateLimitIDs, "global quota must never clear image, Spark or plan restrictions")
}
