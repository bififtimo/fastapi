from celery import Celery

celery = Celery(
    'tasks',
    broker='amqp://host.docker.internal:5672//',
    backend='rpc://'  # Используем RPC для получения результатов задач
)