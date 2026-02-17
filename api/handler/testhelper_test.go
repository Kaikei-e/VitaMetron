package handler

import "vitametron/api/adapter/mlclient"

func newTestMLClient(url string) *mlclient.Client {
	return mlclient.New(url)
}
