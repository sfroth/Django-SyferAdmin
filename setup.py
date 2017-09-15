from setuptools import setup

setup(
    name="syferadmin",
    version="1.1.4",
    author="Stephen Roth",
    author_email="steve@syferweb.com",
    description=("A styled Django admin with built in handling for many common components"),
    license="BSD",
    url="https://github.com/sfroth/Django-SyferAdmin",
    packages=['syferadmin'],
    install_requires=['Django>=1.11.3', 'django-mptt>=0.8.7', 'django-imagekit>=3.3', 'inlinestyler>=0.2.3', 'lxml>=3.4.1', 'pilkit>=1.1.13', 'Pillow>=3.2.0', 'python-dateutil>=2.5.3', 'requests>=2.10.0', 'celery>=3.1.23', 'django-sortedm2m>=1.2.2', 'google-api-python-client>=1.6.2', 'httplib2>=0.9.2', 'oauth2client>=4.0.0', 'openpyxl>=2.2.4', 'httplib2>=0.9.2', 'httplib2>=0.9.2'],
    dependency_links=['http://github.com/sfroth/django-jsonfield.git@a5949393835bf6ae6b073c041441b028fa56aa85#egg=django_jsonfield'],
)
