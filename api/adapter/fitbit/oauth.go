package fitbit

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
	"golang.org/x/oauth2"

	"vitametron/api/domain/port"
	"vitametron/api/infrastructure/config"
	"vitametron/api/infrastructure/crypto"
)

const (
	providerName = "fitbit"
	pkceKeyPrefix = "oauth:pkce:"
	pkceTTL       = 10 * time.Minute
	tokenBufferDuration = 5 * time.Minute
)

type FitbitOAuth struct {
	config     *oauth2.Config
	httpClient *http.Client
	tokenRepo  port.TokenRepository
	redis      *redis.Client
	encryptor  *crypto.Encryptor
}

func NewFitbitOAuth(cfg config.FitbitConfig, rdb *redis.Client, tokenRepo port.TokenRepository, enc *crypto.Encryptor) *FitbitOAuth {
	return &FitbitOAuth{
		config: &oauth2.Config{
			ClientID:     cfg.ClientID,
			ClientSecret: cfg.ClientSecret,
			RedirectURL:  cfg.RedirectURI,
			Scopes: []string{
				"activity",
				"heartrate",
				"oxygen_saturation",
				"respiratory_rate",
				"sleep",
				"temperature",
				"cardio_fitness",
				"profile",
			},
			Endpoint: oauth2.Endpoint{
				AuthURL:   "https://www.fitbit.com/oauth2/authorize",
				TokenURL:  "https://api.fitbit.com/oauth2/token",
				AuthStyle: oauth2.AuthStyleInHeader,
			},
		},
		httpClient: &http.Client{Timeout: 10 * time.Second},
		tokenRepo:  tokenRepo,
		redis:      rdb,
		encryptor:  enc,
	}
}

func (f *FitbitOAuth) AuthorizationURL(ctx context.Context) (string, string, error) {
	verifier := oauth2.GenerateVerifier()

	state, err := generateState()
	if err != nil {
		return "", "", fmt.Errorf("fitbit oauth: generate state: %w", err)
	}

	ok, err := f.redis.SetNX(ctx, pkceKeyPrefix+state, verifier, pkceTTL).Result()
	if err != nil {
		return "", "", fmt.Errorf("fitbit oauth: redis set: %w", err)
	}
	if !ok {
		return "", "", fmt.Errorf("fitbit oauth: state collision")
	}

	authURL := f.config.AuthCodeURL(state, oauth2.S256ChallengeOption(verifier))
	return authURL, state, nil
}

func (f *FitbitOAuth) ExchangeCode(ctx context.Context, code, state string) error {
	verifier, err := f.redis.GetDel(ctx, pkceKeyPrefix+state).Result()
	if err == redis.Nil {
		return fmt.Errorf("fitbit oauth: invalid or expired state")
	}
	if err != nil {
		return fmt.Errorf("fitbit oauth: redis get: %w", err)
	}

	token, err := f.config.Exchange(ctx, code, oauth2.VerifierOption(verifier))
	if err != nil {
		return fmt.Errorf("fitbit oauth: exchange code: %w", err)
	}

	return f.saveToken(ctx, token)
}

func (f *FitbitOAuth) RefreshTokenIfNeeded(ctx context.Context) error {
	_, encRefresh, expiresAt, err := f.tokenRepo.Get(ctx, providerName)
	if err != nil {
		return fmt.Errorf("fitbit oauth: get token: %w", err)
	}

	if time.Now().Before(expiresAt.Add(-tokenBufferDuration)) {
		return nil
	}

	refreshToken, err := f.encryptor.Decrypt(encRefresh)
	if err != nil {
		return fmt.Errorf("fitbit oauth: decrypt refresh token: %w", err)
	}

	oldToken := &oauth2.Token{
		RefreshToken: string(refreshToken),
	}
	newToken, err := f.config.TokenSource(ctx, oldToken).Token()
	if err != nil {
		return fmt.Errorf("fitbit oauth: refresh token: %w", err)
	}

	if err := f.saveToken(ctx, newToken); err != nil {
		log.Printf("CRITICAL: failed to save refreshed token: %v", err)
		return fmt.Errorf("fitbit oauth: save refreshed token: %w", err)
	}

	return nil
}

func (f *FitbitOAuth) IsAuthorized(ctx context.Context) (bool, error) {
	_, _, _, err := f.tokenRepo.Get(ctx, providerName)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func (f *FitbitOAuth) Disconnect(ctx context.Context) error {
	_, encRefresh, _, err := f.tokenRepo.Get(ctx, providerName)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			return nil
		}
		return fmt.Errorf("fitbit oauth: get token for revoke: %w", err)
	}

	refreshToken, err := f.encryptor.Decrypt(encRefresh)
	if err != nil {
		log.Printf("warn: failed to decrypt refresh token for revoke: %v", err)
	} else {
		f.revokeToken(ctx, string(refreshToken))
	}

	return f.tokenRepo.Delete(ctx, providerName)
}

// GetAccessToken returns the decrypted access token. Used by the API client.
func (f *FitbitOAuth) GetAccessToken(ctx context.Context) (string, error) {
	encAccess, _, _, err := f.tokenRepo.Get(ctx, providerName)
	if err != nil {
		return "", fmt.Errorf("fitbit oauth: get token: %w", err)
	}

	accessToken, err := f.encryptor.Decrypt(encAccess)
	if err != nil {
		return "", fmt.Errorf("fitbit oauth: decrypt access token: %w", err)
	}

	return string(accessToken), nil
}

func (f *FitbitOAuth) saveToken(ctx context.Context, token *oauth2.Token) error {
	encAccess, err := f.encryptor.Encrypt([]byte(token.AccessToken))
	if err != nil {
		return fmt.Errorf("encrypt access token: %w", err)
	}

	encRefresh, err := f.encryptor.Encrypt([]byte(token.RefreshToken))
	if err != nil {
		return fmt.Errorf("encrypt refresh token: %w", err)
	}

	return f.tokenRepo.Save(ctx, providerName, encAccess, encRefresh, token.Expiry)
}

func (f *FitbitOAuth) revokeToken(ctx context.Context, refreshToken string) {
	data := url.Values{"token": {refreshToken}}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		"https://api.fitbit.com/oauth2/revoke",
		strings.NewReader(data.Encode()))
	if err != nil {
		log.Printf("warn: failed to create revoke request: %v", err)
		return
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.SetBasicAuth(f.config.ClientID, f.config.ClientSecret)

	resp, err := f.httpClient.Do(req)
	if err != nil {
		log.Printf("warn: fitbit revoke request failed: %v", err)
		return
	}
	resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("warn: fitbit revoke returned status %d", resp.StatusCode)
	}
}

func generateState() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}
