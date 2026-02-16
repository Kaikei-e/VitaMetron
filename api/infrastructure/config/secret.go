package config

import (
	"os"
	"strings"
)

// ReadSecret はファイルパスからシークレットを読み取る。
// ファイルが存在しない場合はフォールバック値を返す。
func ReadSecret(path string, fallback string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		return fallback
	}
	return strings.TrimSpace(string(data))
}
