package service

import (
	"context"
	"log/slog"
	"net/http"
	"strings"
	"time"
)

const openAICodexTextQuotaKey = "openai:codex_text"

// Native Images has its own quota. Responses image tools still need the text
// driver, so image intent alone must never exempt them from Codex text limits.
func isNativeOpenAIImagesQuotaRequest(ctx context.Context, account *Account, requestedModel string) bool {
	return isOpenAIOAuthAccount(account) && isNativeOpenAIImagesQuotaModel(ctx, account.GetMappedModel(requestedModel))
}

func isNativeOpenAIImagesQuotaModel(ctx context.Context, upstreamModel string) bool {
	return OpenAIImagesEndpointFromContext(ctx) && !isOpenAIImagesForceResponses(ctx) && usesCodexDirectImages(upstreamModel)
}

// Explicit exhausted Codex windows describe a capability, not credentials or
// account health. Keep transient 429 retries and terminal/auth errors on their
// existing paths. Spark is handled separately before this method is called.
func (s *RateLimitService) handleOpenAICodexQuotaLimit(ctx context.Context, account *Account, model string, status int, headers http.Header, body []byte) bool {
	if s == nil || s.accountRepo == nil || !isOpenAIOAuthAccount(account) || account.IsShadow() ||
		status != http.StatusTooManyRequests || !account.ShouldHandleErrorCode(status) ||
		!strings.HasPrefix(model, "gpt-") || isCodexSparkModel(model) {
		return false
	}
	disposition, resetAt := classifyOpenAIOAuth429(headers, body)
	if disposition == openAIOAuth429Transient {
		return false
	}
	scope := openAICodexTextQuotaKey
	if isNativeOpenAIImagesQuotaModel(ctx, model) {
		scope = openAIImageGenerationRateLimitKey
	} else if isOpenAIImageGenerationModel(model) {
		// Unknown/legacy image transports retain their existing error policy.
		return false
	}
	if resetAt == nil || !resetAt.After(time.Now()) {
		cooldown, enabled := s.get429FallbackCooldown(ctx, account)
		if !enabled || cooldown <= 0 {
			cooldown = time.Duration(defaultRateLimit429CooldownSeconds) * time.Second
		}
		until := time.Now().Add(cooldown)
		resetAt = &until
	}
	if scope == openAICodexTextQuotaKey {
		persistOpenAI429PlanType(ctx, s.accountRepo, account, body)
		s.persistOpenAICodexSnapshot(ctx, account, headers)
		notifyOpenAIAutoReset(account.ID)
	}
	if err := s.accountRepo.SetModelRateLimit(ctx, account.ID, scope, *resetAt, "openai_codex_capability_quota"); err != nil {
		slog.Warn("openai_codex_capability_quota_write_failed", "account_id", account.ID, "scope", scope, "error", err)
	} else {
		slog.Info("openai_codex_capability_quota_paused", "account_id", account.ID, "scope", scope, "reset_at", *resetAt)
	}
	return true
}
