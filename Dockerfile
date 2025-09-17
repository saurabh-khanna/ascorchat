FROM python:3.12.3-bullseye
SHELL ["/bin/bash", "-c"]
ENV PIP_NO_CACHE_DIR off
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 0
RUN apt-get update \
 && apt-get install -y --force-yes \
 nano python3-pip gettext chrpath libssl-dev libxft-dev \
 libfreetype6 libfreetype6-dev  libfontconfig1 libfontconfig1-dev\
 && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip && pip install --upgrade setuptools && pip install gunicorn
WORKDIR /code/
COPY ./code/requirements.txt /code/
RUN pip install -r requirements.txt
COPY ./code/ /code/
COPY ./env/ /env/
RUN source /env/envs_export.sh && if [ -n "$BUILD_COMMAND" ]; then eval $BUILD_COMMAND; fi
RUN source /env/envs_export.sh && export && if [ -f "manage.py" ]; then if [ "$DISABLE_COLLECTSTATIC" == "1" ]; then echo "collect static disabled"; else echo "Found manage.py, running collectstatic" && python manage.py collectstatic --noinput; fi;  else echo "No manage.py found. Skipping collectstatic."; fi;
RUN useradd -ms /bin/bash code
USER code
