package scheduler

import (
	"context"
	"log"
	"time"

	"vitametron/api/application"
	"vitametron/api/domain/port"
)

type Scheduler struct {
	syncUC   application.SyncUseCase
	oauth    port.OAuthProvider
	interval time.Duration
	stop     chan struct{}
	done     chan struct{}
}

func New(syncUC application.SyncUseCase, oauth port.OAuthProvider, interval time.Duration) *Scheduler {
	return &Scheduler{
		syncUC:   syncUC,
		oauth:    oauth,
		interval: interval,
		stop:     make(chan struct{}),
		done:     make(chan struct{}),
	}
}

func (s *Scheduler) Start() {
	go s.run()
}

func (s *Scheduler) Stop() {
	close(s.stop)
	<-s.done
}

func (s *Scheduler) run() {
	defer close(s.done)

	ticker := time.NewTicker(s.interval)
	defer ticker.Stop()

	for {
		select {
		case <-s.stop:
			return
		case <-ticker.C:
			s.sync()
		}
	}
}

func (s *Scheduler) sync() {
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	authorized, err := s.oauth.IsAuthorized(ctx)
	if err != nil {
		log.Printf("scheduler: failed to check authorization: %v", err)
		return
	}
	if !authorized {
		log.Printf("scheduler: skipping sync (not authorized)")
		return
	}

	if err := s.syncUC.SyncDate(ctx, time.Now()); err != nil {
		log.Printf("scheduler: sync failed: %v", err)
		return
	}

	log.Printf("scheduler: sync completed")
}
