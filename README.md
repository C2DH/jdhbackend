# jdhbackend

backend for our Journal of Digital History

## development (with pipenv)

First of all, make sure that pipenvlock and requirements.txt are synced, then
start the JDH django apps using make.

```
pipenv install -r requirements.txt

make run-dev
```

### SEO configuration in development

THe django app `jdhseo` needs a JDHSEO_PROXY_HOST env variable in the full form
**without the trailing slash** like `https://local-proxy-domain-name`.
Plain `http` protocol can also be used.
The domain name provided should correctly handle the `/proxy-githubusercontent`
path.
By default this value is set to `https://journalofdigitalhistory.org`

### Celery tasks in development

The django app `jdhtasks` is a separate app that should contain all celery tasks.
However, as we use `autodiscover_tasks`, tasks can be added in each app.
As Celery runs together with redis, you have to provide a redis-server somehow.
I suggest to start fresh and use docker:

```
docker run --name jdh-redis -p 6379:6379 -d redis:alpine
```

Then run

```
REDIS_HOST=localhost REDIS_PORT=6379 \
pipenv run celery -A jdhtasks worker -l info
```

to start the celery worker using `pipenv` and your current `.env` file.

To test that everything works fine run in another terminal:

```
REDIS_HOST=localhost REDIS_PORT=6379 \
pipenv run ./manage.py echo "It was a bright cold day in July ..."
```

(source file for this command is at `jdhtasks/management/commands/echo.py`)

### Running tests

Be sure to have your environment activate (if not, do `source .venv/bin/activate`) and then :

`python3 manage.py test`

or with Pip:

`pipenv run ./manage.py test`

### To generate requirements.txt from the pipfile

`pipenv requirements --dev --exclude-markers > requirements.txt`
