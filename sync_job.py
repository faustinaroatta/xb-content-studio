"""Sincroniza las métricas sin abrir la app. Lo corre GitHub Actions todos los días (ver .github/workflows/sync.yml).
También se puede correr a mano:  python sync_job.py
"""
import integrations

if __name__ == "__main__":
    for account, status, n in integrations.sync_all():
        print(f"{account:12} {status} ({n} posts)")
