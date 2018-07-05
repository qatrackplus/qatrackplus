FROM nginx:1.13.0

RUN rm /etc/nginx/conf.d/default.conf

# ADD jupyter /etc/nginx/conf.d/jupyter.conf
ADD django /etc/nginx/conf.d/django.conf
