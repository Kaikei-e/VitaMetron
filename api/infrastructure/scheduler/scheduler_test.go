package scheduler

import (
	"context"
	"sync/atomic"
	"testing"
	"time"
)

// --- stubs ---

type stubSyncUC struct {
	callCount atomic.Int64
}

func (s *stubSyncUC) SyncDate(_ context.Context, _ time.Time) error {
	s.callCount.Add(1)
	return nil
}

type stubOAuth struct {
	authorized bool
}

func (s *stubOAuth) AuthorizationURL(_ context.Context) (string, string, error) {
	return "", "", nil
}
func (s *stubOAuth) ExchangeCode(_ context.Context, _, _ string) error { return nil }
func (s *stubOAuth) RefreshTokenIfNeeded(_ context.Context) error      { return nil }
func (s *stubOAuth) IsAuthorized(_ context.Context) (bool, error)      { return s.authorized, nil }
func (s *stubOAuth) Disconnect(_ context.Context) error                { return nil }

// --- tests ---

func TestScheduler_RunsSync(t *testing.T) {
	syncUC := &stubSyncUC{}
	oauth := &stubOAuth{authorized: true}

	sched := New(syncUC, oauth, 10*time.Millisecond)
	sched.Start()

	time.Sleep(55 * time.Millisecond)
	sched.Stop()

	count := syncUC.callCount.Load()
	if count < 2 {
		t.Errorf("expected at least 2 sync calls, got %d", count)
	}
}

func TestScheduler_SkipsWhenNotAuthorized(t *testing.T) {
	syncUC := &stubSyncUC{}
	oauth := &stubOAuth{authorized: false}

	sched := New(syncUC, oauth, 10*time.Millisecond)
	sched.Start()

	time.Sleep(55 * time.Millisecond)
	sched.Stop()

	count := syncUC.callCount.Load()
	if count != 0 {
		t.Errorf("expected 0 sync calls when not authorized, got %d", count)
	}
}

func TestScheduler_StopsGracefully(t *testing.T) {
	syncUC := &stubSyncUC{}
	oauth := &stubOAuth{authorized: true}

	sched := New(syncUC, oauth, 10*time.Millisecond)
	sched.Start()

	done := make(chan struct{})
	go func() {
		sched.Stop()
		close(done)
	}()

	select {
	case <-done:
		// ok
	case <-time.After(1 * time.Second):
		t.Fatal("Stop did not return within 1 second")
	}
}
