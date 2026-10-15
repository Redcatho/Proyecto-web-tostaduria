import os

from redis import Redis
from rq import Queue

from app.tasks.jobs import health_probe


def main() -> None:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is required")

    queue = Queue("tostaduria", connection=Redis.from_url(redis_url))
    job = queue.enqueue(health_probe)
    print(job.id)


if __name__ == "__main__":
    main()
