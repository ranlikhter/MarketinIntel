web:    cd backend/api && uvicorn main:app --host 0.0.0.0 --port $PORT
worker: cd backend && celery -A celery_app worker --loglevel=info --queues=scraping,analytics,notifications,alerts,integrations,maintenance --concurrency=4
beat:   cd backend && celery -A celery_app beat --loglevel=info --scheduler celery.beat.PersistentScheduler
