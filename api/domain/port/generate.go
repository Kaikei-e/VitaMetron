package port

//go:generate mockgen -source=repository.go -destination=../../mocks/mock_repository.go -package=mocks
//go:generate mockgen -source=biometrics.go -destination=../../mocks/mock_biometrics.go -package=mocks
//go:generate mockgen -source=oauth.go -destination=../../mocks/mock_oauth.go -package=mocks
//go:generate mockgen -source=ml.go -destination=../../mocks/mock_ml.go -package=mocks
