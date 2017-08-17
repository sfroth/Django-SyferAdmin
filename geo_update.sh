#!/bin/bash
# 5 8 * * 3 root [ `date +\%d` -le 7 ] && ./geo_update.sh

# cd /usr/share/geoip  # change to destination folder
curl -O http://geolite.maxmind.com/download/geoip/database/GeoLiteCountry/GeoIP.dat.gz || { echo 'Could not download GeoLiteCountry, exiting.' ; exit 1; }
curl -O http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz || { echo 'Could not download GeoLiteCity, exiting.' ; exit 1; }
gunzip -f GeoIP.dat.gz
gunzip -f GeoLiteCity.dat.gz
